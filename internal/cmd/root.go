package cmd

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"time"

	"github.com/s-hammon/ff12rng"
	"github.com/s-hammon/ff12rng/internal/memscan"
	"github.com/s-hammon/ff12rng/internal/mt"
	"github.com/s-hammon/ff12rng/internal/sig"
	"github.com/spf13/cobra"
)

const (
	MtiSignature = "8B 15 ?? ?? ?? ?? 48 63 ?? 48 8D ?? ?? ?? ?? ?? FF C2 89 15 ?? ?? ?? ?? 8B 0C 81 8B C1 C1 E8 0B 33 C8 8B C1 25 ?? ?? ?? ?? C1 E0 07 33 C8 8B C1 25 ?? ?? ?? ?? C1 E0 0F 33 C8 8B C1 C1 E8 12 33 C1 48 83 C4 28"
	Rows         = 50
	Cols         = 5
)

var rootCmd = &cobra.Command{
	Use:   "ff12rng",
	Short: "track the state of FFXII's PRNG",
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx, cancel := context.WithCancel(cmd.Context())
		defer cancel()

		updates := make(chan ff12rng.Update, 1)
		cfg := WorkerConfig{"FFXII_TZA", MtiSignature, 400}
		go RunWorker(ctx, cfg, updates)

		if err := ff12rng.RunTUI(updates, Rows, Cols); err != nil {
			return fmt.Errorf("tui: %v", err)
		}

		return nil
	},
}

func Execute(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	ctx := context.Background()
	if err := rootCmd.ExecuteContext(ctx); err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			return exitError.ExitCode()
		}

		return 1
	}

	return 0
}

type WorkerConfig struct {
	ProcessSubstring, Signature string
	WantCount                   int
}

func RunWorker(ctx context.Context, cfg WorkerConfig, out chan<- ff12rng.Update) {
	tick := time.NewTicker(250 * time.Millisecond)
	defer tick.Stop()

	var (
		pid       int
		memfile   *os.File
		mtIdxAddr uint64
		pat, _    = sig.ParseSignature(cfg.Signature)
		probe     *mt.Probe
	)

	sendOffline := func(msg string) {
		out <- ff12rng.Update{Online: false, Error: msg}
	}

	reset := func() {
		if memfile != nil {
			_ = memfile.Close()
			memfile = nil
		}

		mtIdxAddr = 0
		probe = nil
	}

	defer func() {
		if memfile != nil {
			_ = memfile.Close()
		}
	}()

	for {
		select {
		case <-ctx.Done():
			return
		case <-tick.C:
			if memfile == nil {
				var err error
				pid, err = memscan.FindPidBySubstring(cfg.ProcessSubstring)
				if err != nil {
					sendOffline("process not found")
					continue
				}

				memfile, err = memscan.OpenMem(pid)
				if err != nil {
					sendOffline("cannot open mem")
					continue
				}
			}

			if mtIdxAddr == 0 {
				regions, err := memscan.ReadMaps(pid)
				if err != nil {
					reset()
					sendOffline("cannot read maps")
					continue
				}

				addr, err := memscan.ScanRegions(memfile, regions, pat)
				if err != nil {
					reset()
					sendOffline("cannot read maps")
					continue
				}

				mtIdxAddr, err = sig.CalcMtIdxAddress(addr, func(addr uint64) (uint32, error) {
					return memscan.ReadUint32(memfile, addr)
				})
				if err != nil {
					reset()
					sendOffline("bad mt index address")
					continue
				}
			}

			snap, err := mt.ReadSnapshot(memfile, mtIdxAddr)
			if err != nil {
				reset()
				sendOffline("bad snapshot")
				continue
			}

			if probe == nil {
				probe = mt.NewProbe(snap)
			}

			if !probe.Sync(snap.State[snap.MtIdx], snap.MtIdx) {
				probe = mt.NewProbe(snap)
			}

			out <- ff12rng.Update{
				Online:       true,
				MtIdx:        probe.Idx(),
				NextPercents: probe.NextPercentages(cfg.WantCount),
			}
		}
	}
}

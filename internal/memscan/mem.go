package memscan

import (
	"bufio"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/s-hammon/ff12rng/internal/sig"
	"github.com/s-hammon/p"
)

// Memory Map Region
type Region struct {
	Start, End uint64
	Perms      string
}

type ProcessMemory struct {
	pid     int
	mem     *os.File
	regions []Region
}

func NewProcessMemory(pid int) *ProcessMemory {
	return &ProcessMemory{pid: pid}
}

func (pm *ProcessMemory) Open() error {
	mem, err := OpenMem(pm.pid)
	if err != nil {
		return err
	}

	pm.mem = mem
	return nil
}

func (pm *ProcessMemory) Close() error {
	if pm.mem == nil {
		return errors.New("trying to close nil file")
	}
	return pm.mem.Close()
}

func (pm *ProcessMemory) Regions() []Region {
	if len(pm.regions) == 0 {
		regions, err := ReadMaps(pm.pid)
		if err != nil {
			panic(err)
		}

		pm.regions = regions
	}

	out := make([]Region, len(pm.regions))
	copy(out, pm.regions)
	return out
}

func (pm *ProcessMemory) FindSignature(s string) *uint64 {
	pat, err := sig.ParseSignature(s)
	if err != nil {
		return nil
	}

	for _, region := range pm.Regions() {
		if !strings.Contains(region.Perms, "r") {
			continue
		}

		size := int(region.End - region.Start)
		buf := make([]byte, size)
		if _, err := pm.mem.ReadAt(buf, int64(region.Start)); err != nil {
			continue
		}

		if off := pat.Find(buf); off != -1 {
			addr := region.Start + uint64(off)
			return &addr
		}
	}

	return nil
}

func (pm *ProcessMemory) ReadMemory(addr uint64, count int) ([]byte, error) {
	if pm.mem == nil {
		return nil, errors.New("memory not open")
	}
	if _, err := pm.mem.Seek(int64(addr), io.SeekStart); err != nil {
		return nil, fmt.Errorf("read 0x%x (%d): %v", addr, count, err)
	}

	buf := make([]byte, count)
	if _, err := io.ReadFull(pm.mem, buf); err != nil {
		return nil, fmt.Errorf("read 0x%x (%d): %v", addr, count, err)
	}

	return buf, nil
}

func (pm *ProcessMemory) ReadUint32(addr uint64) (uint32, error) {
	b, err := pm.ReadMemory(addr, 4)
	if err != nil {
		return 0, err
	}

	return binary.LittleEndian.Uint32(b), nil
}

func FindPidBySubstring(substr string) (int, error) {
	ents, err := os.ReadDir("/proc")
	if err != nil {
		return 0, err
	}

	for _, e := range ents {
		if !e.IsDir() {
			continue
		}

		pid, err := strconv.Atoi(e.Name())
		if err != nil {
			continue
		}

		commBytes, err := os.ReadFile(p.Format("/proc/%d/comm", pid))
		if err != nil {
			continue
		}

		comm := strings.TrimSpace(string(commBytes))
		if strings.Contains(comm, substr) {
			return pid, nil
		}
	}

	return 0, fmt.Errorf("process containing %s not found", substr)
}

func ReadMaps(pid int) ([]Region, error) {
	f, err := os.Open(p.Format("/proc/%d/maps", pid))
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var regs []Region
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}

		addr := strings.Split(fields[0], "-")
		if len(addr) != 2 {
			continue
		}

		start, err1 := strconv.ParseUint(addr[0], 16, 64)
		end, err2 := strconv.ParseUint(addr[1], 16, 64)
		if err1 != nil || err2 != nil {
			continue
		}

		regs = append(regs, Region{Start: start, End: end, Perms: fields[1]})
	}

	return regs, scanner.Err()
}

func OpenMem(pid int) (*os.File, error) {
	return os.OpenFile(p.Format("/proc/%d/mem", pid), os.O_RDONLY, 0)
}

func ReadUint32(f *os.File, addr uint64) (uint32, error) {
	var buf [4]byte
	_, err := f.ReadAt(buf[:], int64(addr))
	return binary.LittleEndian.Uint32(buf[:]), err
}

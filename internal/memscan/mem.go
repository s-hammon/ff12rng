package memscan

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/s-hammon/p"
)

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

// Memory-mapped region from "/proc/{pid}/maps"
type Region struct {
	Start, End uint64
	Perms      string
}

// Read the mem map of a given PID and returns the list of Regions
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

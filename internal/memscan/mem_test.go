package memscan

import (
	"os"
	"strings"
	"testing"

	"github.com/s-hammon/ff12rng/internal/sig"
	"github.com/stretchr/testify/require"
)

func TestReadMaps(t *testing.T) {
	pid := os.Getpid()
	regions, err := ReadMaps(pid)
	require.NoError(t, err)
	require.Greater(t, len(regions), 0)

	hasReadable := false
	for _, region := range regions {
		if strings.Contains(region.Perms, "r") {
			hasReadable = true
			break
		}
	}

	require.True(t, hasReadable)
}

func TestMemoryRegions(t *testing.T) {
	pid := os.Getpid()
	regions, err := ReadMaps(pid)
	require.NoError(t, err)
	require.Greater(t, len(regions), 0)

	foundReadable := false
	for _, region := range regions {
		if strings.Contains(region.Perms, "r") {
			foundReadable = true
			break
		}
	}

	require.True(t, foundReadable)
}

func TestReadUint32(t *testing.T) {
	pid := os.Getpid()
	pm := NewProcessMemory(pid)
	require.NoError(t, pm.Open())
	defer pm.Close()

	regions := pm.Regions()
	require.NotEmpty(t, regions)

	var success bool
	for _, region := range regions {
		if !strings.HasPrefix(region.Perms, "r") {
			continue
		}

		_, err := pm.ReadUint32(region.Start)
		if err == nil {
			success = true
			break
		}
	}

	require.True(t, success, "unable to read from any readable memory region")
}

func TestParseSignatureAndFind(t *testing.T) {
	buf := []byte{0xDE, 0xAD, 0xBE, 0xEF, 0x90, 0x5A, 0x10, 0x99}
	pat, err := sig.ParseSignature("90 5A ?? 99")
	require.NoError(t, err)

	offset := pat.Find(buf)
	require.Equal(t, 4, offset)
}

func TestProcessMemoryCaching(t *testing.T) {
	pid := os.Getpid()
	regions, err := ReadMaps(pid)
	require.NoError(t, err)

	pm := &ProcessMemory{pid: pid, regions: regions}

	reg1 := pm.Regions()
	reg2 := pm.Regions()
	require.Equal(t, len(reg1), len(reg2))
}

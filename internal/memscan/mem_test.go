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

func TestParseSignatureAndFind(t *testing.T) {
	buf := []byte{0xDE, 0xAD, 0xBE, 0xEF, 0x90, 0x5A, 0x10, 0x99}
	pat, err := sig.ParseSignature("90 5A ?? 99")
	require.NoError(t, err)

	offset := pat.Find(buf)
	require.Equal(t, 4, offset)
}

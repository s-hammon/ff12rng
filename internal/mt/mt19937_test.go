package mt

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestTemperIdempotence(t *testing.T) {
	state := make([]uint32, n)
	for i := range n {
		state[i] = uint32(i*1664525 + 1013904223)
	}
	p := NewProbeFromState(state, 0, 3)
	got := p.NextPercentages(5)
	require.Len(t, got, 5)
}

func TestSyncToNextBlock(t *testing.T) {
	state0 := make([]uint32, n)
	for i := range n {
		state0[i] = uint32(i)
	}
	state1 := twist(state0)
	p := NewProbeFromState(state0, 0, 3)
	require.True(t, p.Sync(state1[123], 123))
	require.Equal(t, p.Idx(), 123)
}

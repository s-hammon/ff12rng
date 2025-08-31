package mt

import (
	"encoding/binary"
	"os"

	"github.com/s-hammon/ff12rng/internal/util"
)

type Snapshot struct {
	State [n]uint32
	MtIdx int
}

func ReadSnapshot(mem *os.File, mtIdxAddr uint64) (Snapshot, error) {
	base := mtIdxAddr - uint64(n*4)
	raw, err := util.ReadBytes(mem, base, (n+1)*4)
	if err != nil {
		return Snapshot{}, err
	}

	var snap Snapshot
	for i := range n {
		snap.State[i] = binary.LittleEndian.Uint32(raw[i*4 : i*4+4])
	}

	mtIdx := int(binary.LittleEndian.Uint32(raw[n*4:n*4+4])) % n
	if mtIdx < 0 {
		mtIdx += n
	}

	snap.MtIdx = mtIdx
	return snap, nil
}

func NewProbe(snap Snapshot) *Probe {
	return NewProbeFromState(snap.State[:], snap.MtIdx, 10)
}

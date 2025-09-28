package mt

const (
	n         int    = 624
	m         int    = 397
	matrixA   uint32 = 0x9908B0DF
	upperMask uint32 = 0x80000000 // most significant bit
	lowerMask uint32 = 0x7FFFFFFF // least significant bit
)

// twist and temper are the core MT19937 transformation/bit shuffling algo,
// respectively. No reason to touch these since we're not actually writing to
// the game's memory.
func twist(current []uint32) []uint32 {
	next := make([]uint32, n)
	for i := range n {
		y := (current[i] & upperMask) | (current[(i+1)%n] & lowerMask)
		yA := y >> 1
		if (y & 1) != 0 {
			yA ^= matrixA
		}
		next[i] = current[(i+m)%n] ^ yA
	}
	return next
}

func temper(y uint32) uint32 {
	y ^= (y >> 11)
	y ^= (y << 7) & 0x9D2C5680
	y ^= (y << 15) & 0xEFC60000
	y ^= (y >> 18)
	return y
}

// Probe tracks the internal generator state, and provides a look-ahead to the
// next state.
type Probe struct {
	states   [][]uint32
	idx      int
	maxAhead int
}

// Create an object from the initial state (i.e. the signature parsed from the
// procmem). Subsequent states are monitored using Probe.Sync
func NewProbeFromState(mt []uint32, idx int, maxAhead int) *Probe {
	if len(mt) != n {
		panic("NewProbeFromState: mt must have length 624")
	}

	cp := make([]uint32, n)
	copy(cp, mt)
	return &Probe{
		states:   [][]uint32{cp},
		idx:      idx % n,
		maxAhead: maxAhead,
	}
}

// Display the next n tempered values in the form of percent (0-99)
func (p *Probe) NextPercentages(n int) []int {
	out := make([]int, n)
	for i := range n {
		out[i] = int(p.temperedAt(i) % 100)
	}

	return out
}

// Sync the Probe to an observed in-memory value.
func (p *Probe) Sync(observed uint32, obsIdx int) bool {
	if obsIdx < 0 || obsIdx >= n {
		return false
	}

	for len(p.states) < p.maxAhead {
		p.states = append(p.states, twist(p.states[len(p.states)-1]))
	}

	for i, st := range p.states {
		if st[obsIdx] == observed {
			p.states = append([][]uint32{}, p.states[i:]...)
			p.idx = obsIdx
			return true
		}
	}
	return false
}

func (p *Probe) Idx() int {
	return p.idx
}

func (p *Probe) ensure(abs int) {
	targetPos := p.idx + abs
	needStates := targetPos/n + 1
	for len(p.states) < needStates {
		next := twist(p.states[len(p.states)-1])
		p.states = append(p.states, next)
	}

	if p.maxAhead > 0 && len(p.states) > p.maxAhead {
		drop := len(p.states) - p.maxAhead
		p.states = append([][]uint32{}, p.states[drop:]...)
		if p.idx >= n {
			p.idx = p.idx % n
		}
	}
}

func (p *Probe) temperedAt(abs int) uint32 {
	p.ensure(abs)
	pos := p.idx + abs
	state := p.states[pos/n]
	off := pos % n
	return temper(state[off])
}

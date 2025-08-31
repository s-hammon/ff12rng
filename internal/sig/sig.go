package sig

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/s-hammon/p"
)

const WildcardByte = 0x00

type Pattern struct {
	Bytes []byte
	Mask  []bool
}

func ParseSignature(s string) (Pattern, error) {
	var (
		b []byte
		m []bool
	)
	for tok := range strings.FieldsSeq(s) {
		switch tok {
		case "??", "?":
			b = append(b, WildcardByte)
			m = append(m, true)
		default:
			if len(tok) != 2 {
				return Pattern{}, fmt.Errorf("bad token %q", tok)
			}
			v, err := strconv.ParseUint(tok, 16, 8)
			if err != nil {
				return Pattern{}, fmt.Errorf("bad hex %q: %v", tok, err)
			}
			b = append(b, byte(v))
			m = append(m, false)
		}
	}

	return Pattern{b, m}, nil
}

func (p *Pattern) MatchAt(buf []byte, off int) bool {
	if off+len(p.Bytes) > len(buf) {
		return false
	}

	for i := range p.Bytes {
		if p.Mask[i] {
			continue
		}
		if buf[off+i] != p.Bytes[i] {
			return false
		}
	}

	return true
}

func (p Pattern) Find(buf []byte) int {
	for i := 0; i+len(p.Bytes) <= len(buf); i++ {
		if p.MatchAt(buf, i) {
			return i
		}
	}

	return -1
}

func (pa Pattern) String() string {
	var parts []string
	for i, b := range pa.Bytes {
		if pa.Mask[i] {
			parts = append(parts, "??")
		} else {
			parts = append(parts, p.Format("%02X", b))
		}
	}

	return strings.Join(parts, " ")
}

type Read4 func(addr uint64) (uint32, error)

func CalcMtIdxAddress(sigStart uint64, read4 Read4) (uint64, error) {
	imm, err := read4(sigStart + 2)
	if err != nil {
		return 0, err
	}

	disp := int64(int32(imm))
	nextIP := int64(sigStart + 6)
	return uint64(nextIP + disp), nil
}

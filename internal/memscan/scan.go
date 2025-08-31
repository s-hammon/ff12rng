package memscan

import (
	"errors"
	"os"

	"github.com/s-hammon/ff12rng/internal/sig"
)

func ScanRegions(memfile *os.File, regions []Region, pat sig.Pattern) (uint64, error) {
	const chunk = 1 << 20
	overlap := len(pat.Bytes) - 1
	carry := []byte{}

	for _, r := range regions {
		size := int(r.End - r.Start)
		for off := 0; off < size; {
			toRead := min(size-off, chunk)
			buf := make([]byte, len(carry)+toRead)
			copy(buf, carry)
			if _, err := memfile.ReadAt(buf[len(carry):], int64(r.Start)+int64(off)); err != nil {
				off += toRead
				carry = nil
				continue
			}

			for i := 0; i+len(pat.Bytes) <= len(buf); i++ {
				if pat.MatchAt(buf, i) {
					abs := r.Start + uint64(off+i) - uint64(len(carry))
					return abs, nil
				}
			}

			if overlap > 0 && len(buf) >= overlap {
				carry = append(carry[:0], buf[len(buf)-overlap:]...)
			} else {
				carry = nil
			}

			off += toRead
		}

		carry = nil
	}

	return 0, errors.New("signature not found")
}

package util

import "os"

func ReadBytes(f *os.File, addr uint64, size int) ([]byte, error) {
	buf := make([]byte, size)
	_, err := f.ReadAt(buf, int64(addr))
	return buf, err
}

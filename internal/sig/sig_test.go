package sig

import "testing"

func FuzzParseSignature(f *testing.F) {
	f.Add("90 5A ?? 99")
	f.Fuzz(func(t *testing.T, a string) {
		_, _ = ParseSignature(a)
	})
}

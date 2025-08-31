package main

import (
	"os"

	"github.com/s-hammon/ff12rng/internal/cmd"
)

func main() {
	os.Exit(cmd.Execute(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

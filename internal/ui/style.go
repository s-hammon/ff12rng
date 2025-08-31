package ui

import "github.com/gdamore/tcell/v2"

var (
	StyleBox   = tcell.StyleDefault.Foreground(tcell.ColorGray)
	StyleText  = tcell.StyleDefault.Foreground(tcell.ColorWhite)
	StyleMatch = tcell.StyleDefault.Background(tcell.ColorGreenYellow).Foreground(tcell.ColorBlack).Bold(true)
	StyleDim   = tcell.StyleDefault.Foreground(tcell.ColorGray)
	StyleCyan  = tcell.StyleDefault.Foreground(tcell.ColorLightCyan).Bold(true)
	StyleOK    = tcell.StyleDefault.Foreground(tcell.ColorGreen).Bold(true)
	StyleFail  = tcell.StyleDefault.Foreground(tcell.ColorRed).Bold(true)
)

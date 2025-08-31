package ui

import "github.com/gdamore/tcell/v2"

const (
	cellWidth   = 8
	boxPaddingX = 2
	boxPaddingY = 1
)

type UILayout struct {
	Rows      int
	Cols      int
	BoxWidth  int
	StatusY   int
	HelpY     int
	CellWidth int
	PaddingX  int
	PaddingY  int
}

func ComputeLayout(screenW, screenH, cols int) UILayout {
	const fixedRows = 3 + 2 + 3 + 2 // headers, borders, spacing
	rows := max(screenH-fixedRows, 1)

	boxW := cols*cellWidth + boxPaddingX*2
	statusY := 4 + rows + 1
	helpY := statusY + 3

	return UILayout{
		Rows:      rows,
		Cols:      cols,
		BoxWidth:  boxW,
		StatusY:   statusY,
		HelpY:     helpY,
		CellWidth: cellWidth,
		PaddingX:  boxPaddingX,
		PaddingY:  boxPaddingY,
	}
}

func DrawBox(s tcell.Screen, x, y, w, h int, style tcell.Style, title string) {
	s.SetContent(x, y, '┌', nil, style)
	for i := 1; i < w-1; i++ {
		s.SetContent(x+i, y, '─', nil, style)
	}
	s.SetContent(x+w-1, y, '┐', nil, style)

	for j := 1; j < h-1; j++ {
		s.SetContent(x, y+j, '│', nil, style)
		s.SetContent(x+w-1, y+j, '│', nil, style)
	}

	s.SetContent(x, y+h-1, '└', nil, style)
	for i := 1; i < w-1; i++ {
		s.SetContent(x+i, y+h-1, '─', nil, style)
	}
	s.SetContent(x+w-1, y+h-1, '┘', nil, style)

	if title != "" && len(title)+4 < w {
		DrawText(s, x+2, y, style, " "+title+" ")
	}
}

func DrawText(s tcell.Screen, x, y int, style tcell.Style, text string) {
	for i, r := range text {
		s.SetContent(x+i, y, r, nil, style)
	}
}

func DrawTextCentered(s tcell.Screen, centerX, y int, style tcell.Style, text string) {
	startX := centerX - len(text)/2
	DrawText(s, startX, y, style, text)
}

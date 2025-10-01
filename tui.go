package ff12rng

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/gdamore/tcell/v2"
	"github.com/s-hammon/ff12rng/internal/ui"
	"github.com/s-hammon/p"
)

type Threshold struct {
	Value          int
	EqualOrGreater bool
}

type Update struct {
	Online       bool
	MtIdx        int
	NextPercents []int
	Error        string
}

func ParsePattern(s string) ([]Threshold, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil, nil
	}

	parts := strings.Split(s, ",")
	out := make([]Threshold, 0, len(parts))

	for _, part := range parts {
		part = strings.TrimSpace(part)
		eog := strings.HasSuffix(part, "+")
		num := strings.TrimSuffix(part, "+")

		v, err := strconv.Atoi(num)
		if err != nil {
			return nil, fmt.Errorf("strconv.Atoi(%s): %v", num, err)
		}

		out = append(out, Threshold{Value: v, EqualOrGreater: eog})
	}

	return out, nil
}

func MatchSequence(vals []int, pattern []Threshold) map[int]struct{} {
	hits := make(map[int]struct{})
	patternLen := len(pattern)

	if patternLen == 0 {
		return hits
	}

	limit := len(vals) - patternLen
	for i := range limit {
		ok := true
		for j, th := range pattern {
			if th.EqualOrGreater {
				if vals[i+j] < th.Value {
					ok = false
					break
				}
			} else {
				if vals[i+j] != th.Value {
					ok = false
					break
				}
			}
		}

		if ok {
			for j := range pattern {
				hits[i+j] = struct{}{}
			}
		}
	}

	return hits
}

func ColumnMajor(vals []int, rows, cols int) []int {
	out := make([]int, 0, len(vals))
	for c := range cols {
		for r := range rows {
			idx := r + c*rows
			if idx < len(vals) {
				out = append(out, vals[idx])
			}
		}
	}

	return out
}

func RunTUI(updates <-chan Update, rows, cols int) error {
	s, err := tcell.NewScreen()
	if err != nil {
		return fmt.Errorf("tcell.NewScreen: %v", err)
	}
	if err := s.Init(); err != nil {
		return fmt.Errorf("screen.Init: %v", err)
	}
	defer s.Fini()

	var (
		input   string
		pattern []Threshold
		matches map[int]struct{}
		last    Update
	)

	redraw := func() {
		s.Clear()
		s.Sync()

		scrW, scrH := s.Size()
		layout := ui.ComputeLayout(scrW, scrH, cols)

		vals := last.NextPercents
		valCount := layout.Rows * cols
		if len(vals) < valCount {
			vals = append(vals, make([]int, valCount-len(vals))...)
		} else {
			vals = vals[:valCount]
		}

		flat := ColumnMajor(vals, layout.Rows, cols)
		if len(pattern) > 0 && last.Online {
			matches = MatchSequence(flat, pattern)
		} else {
			matches = map[int]struct{}{}
		}

		startX := max((scrW-layout.BoxWidth)/2, 0)

		// Search box
		ui.DrawBox(s, startX, 0, layout.BoxWidth, 3, ui.StyleBox, "CURRENT SEARCH")
		ui.DrawText(s, startX+layout.PaddingX, 1, ui.StyleCyan, input)

		// Main grid
		ui.DrawBox(s, startX, 3, layout.BoxWidth, layout.Rows+2, ui.StyleBox, "")
		for c := range cols {
			for r := range layout.Rows {
				idx := r + c*layout.Rows
				if idx >= len(flat) {
					continue
				}

				val := flat[idx]
				cell := p.Format("%3d:%2d", idx, val)
				style := ui.StyleText
				if _, ok := matches[idx]; ok {
					style = ui.StyleMatch
				}

				x := startX + layout.PaddingX + c*layout.CellWidth
				y := 4 + r
				ui.DrawText(s, x, y, style, cell)
			}
		}

		// Status box
		ui.DrawBox(s, startX, layout.StatusY, layout.BoxWidth, 3, ui.StyleBox, "")
		statetext := "ONLINE"
		statestyle := ui.StyleOK
		if !last.Online {
			statetext = "OFFLINE"
			statestyle = ui.StyleFail
		}

		ui.DrawTextCentered(s, startX+layout.BoxWidth/2, layout.StatusY+1, statestyle, statetext)

		// Help line
		help := "Esc/Ctrl+C: quit  |  Enter: apply pattern  |  Backspace: delete"
		ui.DrawTextCentered(s, scrW/2, layout.HelpY, ui.StyleDim, help)
		s.Show()
	}

	go func() {
		for u := range updates {
			last = u
			if len(pattern) > 0 && last.Online {
				matches = MatchSequence(u.NextPercents, pattern)
			} else {
				matches = nil
			}

			redraw()
		}
	}()

	redraw()

loop:
	for {
		ev := s.PollEvent()
		switch ev := ev.(type) {
		case *tcell.EventKey:
			switch ev.Key() {
			default:
				if ev.Rune() != 0 {
					input += string(ev.Rune())
				}
			case tcell.KeyEscape, tcell.KeyCtrlC:
				break loop
			case tcell.KeyEnter:
				if pat, err := ParsePattern(input); err == nil {
					pattern = pat
					if last.Online {
						matches = MatchSequence(last.NextPercents, pattern)
					} else {
						matches = nil
					}
				}
			case tcell.KeyBackspace, tcell.KeyBackspace2:
				if len(input) > 0 {
					input = input[:len(input)-1]
				}
			}

			redraw()
		case *tcell.EventResize:
			s.Sync()
			redraw()
		}
	}

	return nil
}

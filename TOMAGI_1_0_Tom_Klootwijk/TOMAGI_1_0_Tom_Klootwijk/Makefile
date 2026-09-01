PYTHON ?= python3
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Wpedantic
ifeq ($(OS),Windows_NT)
EXEEXT := .exe
else
EXEEXT :=
endif
C_BACKEND := build/tomagi-c$(EXEEXT)
TOMAGI := $(PYTHON) -c "import runpy,sys;sys.path.insert(0,'src/python');runpy.run_module('tomagi',run_name='__main__')"

.PHONY: all specs figures examples test validate report package clean

all: specs $(C_BACKEND) examples

specs:
	$(PYTHON) tools/build_spec_assets.py
	$(PYTHON) tools/generate_tex_assets.py

figures: examples
	$(PYTHON) tools/generate_figures.py

$(C_BACKEND): src/c/tomagi.c src/c/tomagi_cli.c src/c/tomagi.h
	$(PYTHON) -c "from pathlib import Path;Path('build').mkdir(exist_ok=True)"
	$(CC) $(CFLAGS) -Isrc/c src/c/tomagi.c src/c/tomagi_cli.c -o $@

examples:
	$(TOMAGI) compile examples/polar_loop.json examples/polar_loop.tmg
	$(TOMAGI) run examples/polar_loop.tmg --trace --output examples/polar_loop.expected.json
	$(TOMAGI) compile examples/exact19_rule.json examples/exact19_rule.tmg
	$(TOMAGI) run examples/exact19_rule.tmg --trace --output examples/exact19_rule.expected.json
	$(TOMAGI) compile examples/tomagi_state_orbit.json examples/tomagi_state_orbit.tmg
	$(TOMAGI) run examples/tomagi_state_orbit.tmg --ticks 640 --trace --output examples/tomagi_state_orbit.trace.json
	$(TOMAGI) compile examples/tomagi_state_2d.json examples/tomagi_state_2d.tmg
	$(TOMAGI) materialize examples/tomagi_state_2d.tmg examples/tomagi_state_2d.svg --manifest examples/tomagi_state_2d.manifest.json
	$(TOMAGI) compile examples/tomagi_state_3d.json examples/tomagi_state_3d.tmg
	$(TOMAGI) materialize examples/tomagi_state_3d.tmg examples/tomagi_state_3d.obj --manifest examples/tomagi_state_3d.manifest.json
	$(TOMAGI) compile examples/tomagi_state_4d.json examples/tomagi_state_4d.tmg
	$(TOMAGI) materialize examples/tomagi_state_4d.tmg examples/tomagi_state_4d.csv --manifest examples/tomagi_state_4d.manifest.json
	$(TOMAGI) nineteen --output examples/nineteen_hinge.expected.json

test: all
	$(PYTHON) -c "from pathlib import Path;Path('validation').mkdir(exist_ok=True)"
	$(PYTHON) tools/run_validation.py --run-tests validation/tests.txt

validate: specs test figures
	$(PYTHON) tools/run_validation.py

report: validate
	cd report && pdflatex -interaction=nonstopmode -halt-on-error TOMAGI_1_0_Tom_Klootwijk.tex >/dev/null
	cd report && pdflatex -interaction=nonstopmode -halt-on-error TOMAGI_1_0_Tom_Klootwijk.tex >/dev/null
	cd report && pdflatex -interaction=nonstopmode -halt-on-error TOMAGI_1_0_Tom_Klootwijk.tex >/dev/null

package: report
	$(PYTHON) tools/finalize_package.py

clean:
	rm -rf build dist .pytest_cache __pycache__
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f examples/*.tmg examples/*.expected.json
	rm -f examples/tomagi_state_orbit.trace.json
	rm -f examples/tomagi_state_2d.svg examples/tomagi_state_2d.manifest.json
	rm -f examples/tomagi_state_3d.obj examples/tomagi_state_3d.manifest.json
	rm -f examples/tomagi_state_4d.csv examples/tomagi_state_4d.manifest.json
	rm -f report/*.aux report/*.fdb_latexmk report/*.fls report/*.log report/*.out report/*.toc report/*.lof report/*.lot

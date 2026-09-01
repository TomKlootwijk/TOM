PYTHON ?= python3
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Wpedantic
PYTHONPATH_ENV = PYTHONPATH=src/python

.PHONY: all original-examples counter-world benchmark roadmap-artifact release-artifact static test validate-core validate clean-rebuild package clean-generated clean

all: build/tomagi-c original-examples counter-world benchmark roadmap-artifact release-artifact

build/tomagi-c: src/c/tomagi.c src/c/tomagi_cli.c src/c/tomagi.h
	mkdir -p build
	$(CC) $(CFLAGS) -Isrc/c src/c/tomagi.c src/c/tomagi_cli.c -o $@

original-examples:
	$(PYTHONPATH_ENV) $(PYTHON) -m tomagi compile examples/polar_loop.json examples/polar_loop.tmg >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) -m tomagi run examples/polar_loop.tmg --trace --output examples/polar_loop.expected.json >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) -m tomagi compile examples/exact19_rule.json examples/exact19_rule.tmg >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) -m tomagi run examples/exact19_rule.tmg --trace --output examples/exact19_rule.expected.json >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) -m tomagi nineteen --output examples/nineteen_hinge.expected.json >/dev/null

counter-world: build/tomagi-c
	mkdir -p validation world
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_counter_world.py >/dev/null

benchmark: counter-world
	mkdir -p validation/index_benchmark world
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_index_benchmark.py >/dev/null

roadmap-artifact: build/tomagi-c
	mkdir -p validation artifacts examples/artifacts
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_roadmap_artifact.py >/dev/null

release-artifact: build/tomagi-c
	mkdir -p validation artifacts examples/artifacts
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_0_2_release_artifact.py >/dev/null

static: benchmark roadmap-artifact release-artifact
	mkdir -p validation
	$(PYTHONPATH_ENV) $(PYTHON) tools/verify_static_assets.py > validation/static_assets.json

test: all
	mkdir -p validation
	$(PYTHONPATH_ENV) $(PYTHON) -m unittest discover -s tests -v 2>&1 | tee validation/tests.txt

validate-core: test static
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_world_validation.py

clean-rebuild:
	$(PYTHONPATH_ENV) $(PYTHON) tools/verify_clean_rebuild.py

validate: validate-core clean-rebuild
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_world_validation.py --include-clean

package: validate
	$(PYTHONPATH_ENV) $(PYTHON) tools/finalize_package.py

clean-generated:
	rm -rf build world/counter_store world/index_benchmark_store
	rm -f examples/polar_loop.tmg examples/polar_loop.expected.json
	rm -f examples/exact19_rule.tmg examples/exact19_rule.expected.json
	rm -f examples/nineteen_hinge.expected.json
	rm -f examples/world_counter/counter_program.json examples/world_counter/counter_program.tmg
	rm -f examples/world_counter/initial_transaction.json
	rm -f examples/artifacts/roadmap_and_starter.source.json
	rm -f examples/artifacts/roadmap_and_starter.tmg examples/artifacts/roadmap_and_starter.tmg.compile.json
	rm -f examples/artifacts/world_query_kernel_0_2_release.source.json
	rm -f examples/artifacts/world_query_kernel_0_2_release.tmg examples/artifacts/world_query_kernel_0_2_release.tmg.compile.json
	rm -f artifacts/TOM_AGI_ROADMAP_AND_STARTER.md artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md
	rm -rf validation
	mkdir -p validation
	rm -f checksums/SHA256SUMS.txt checksums/PACKAGE_MANIFEST.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

clean: clean-generated
	rm -rf dist .pytest_cache

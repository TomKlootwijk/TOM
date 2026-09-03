PYTHON ?= python3
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Wpedantic
PYTHONPATH_ENV = PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/python

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

# TOM World & Query Kernel 0.3 interval-event extension.
.PHONY: world03 test-world03 validate-world03 package-world03
world03: build/tomagi-c
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_world03_fixture.py
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_world03_release_artifact.py

test-world03: world03
	$(PYTHONPATH_ENV) $(PYTHON) -m unittest tests.test_world03_interval_events -v

validate-world03: world03
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_world03_validation.py

package-world03: validate-world03
	$(PYTHONPATH_ENV) $(PYTHON) tools/package_world03_release.py

# TOM World & Query Kernel 0.4.1 corrective rebuild.
# This line starts only from the pinned corrected 0.3 sources.  The superseded
# tom_world04 namespace and its relation-authored continuation boundaries are
# deliberately absent.
.PHONY: world04r test-world04r validate-world04r package-world04r clean-world04r

world04r: build/tomagi-c
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_world04r_fixture.py
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_world04r_release_artifact.py

test-world04r: world04r
	$(PYTHONPATH_ENV) $(PYTHON) -m unittest discover -s tests -v

validate-world04r: world04r
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_world04r_validation.py

package-world04r: validate-world04r
	$(PYTHONPATH_ENV) $(PYTHON) tools/package_world04r_release.py

clean-world04r:
	rm -rf examples/world04r/continuation_store validation/world04r
	rm -f examples/world04r/piecewise_reference.tmg
	rm -f examples/world04r/world04r_release_artifact.tmg
	rm -f examples/world04r/world04r_release_artifact.tmg.compile.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# TOM Learner 0.1 / World & Query Kernel 0.5.1 corrective handoff.
.PHONY: learner05 test-learner05 validate-learner05-core clean-rebuild-learner05 validate-learner05 package-learner05 clean-learner05

learner05: build/tomagi-c
	mkdir -p validation/learner05 examples/learner05/datasets
	$(PYTHONPATH_ENV) $(PYTHON) -m tom_learner05 verify-corrective-handoff . --output validation/learner05/corrective_handoff_verification.json >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner05_fixture.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner05_formal_authority.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_corrective_handoff_artifact.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner05_release_artifact.py >/dev/null

test-learner05: learner05
	mkdir -p validation/learner05
	$(PYTHONPATH_ENV) $(PYTHON) -m unittest discover -s tests -v 2>&1 | $(PYTHON) tools/verify_learner05_clean_rebuild.py --canonicalize-test-log validation/learner05/tests.txt

validate-learner05-core: test-learner05
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner05_validation.py

clean-rebuild-learner05: validate-learner05-core
	$(PYTHONPATH_ENV) $(PYTHON) tools/verify_learner05_clean_rebuild.py

validate-learner05: validate-learner05-core clean-rebuild-learner05
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner05_validation.py --include-clean

package-learner05: validate-learner05
	$(PYTHONPATH_ENV) $(PYTHON) tools/package_learner05_release.py

clean-learner05:
	rm -rf examples/learner05/datasets examples/learner05/learner_store validation/learner05
	rm -f examples/learner05/benchmark_manifest.json examples/learner05/benchmark_oracle.json
	rm -f examples/learner05/learner05_formal_authority.tmg examples/learner05/learner05_formal_authority.tmg.compile.json
	rm -f examples/learner05/corrective_handoff_0_5_1.tmg examples/learner05/corrective_handoff_0_5_1.tmg.compile.json
	rm -f TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md
	rm -f examples/learner05/learner05_release_artifact.tmg examples/learner05/learner05_release_artifact.tmg.compile.json
	rm -f checksums/PACKAGE_MANIFEST.json checksums/SHA256SUMS.txt
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# TOM Learner 0.1 / World & Query Kernel 0.5.2 transaction authority.
# The learner family remains exact affine. This target completes the CODEX
# corrective prerequisite by moving promotion/evidence semantics into static
# formal definitions before any broader learner is introduced.
.PHONY: learner052 test-learner052 validate-learner052-core clean-rebuild-learner052 validate-learner052 package-learner052 clean-learner052

learner052: build/tomagi-c
	mkdir -p validation/learner052 examples/learner052
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner052_continuation_handoff.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner052_promotion_authority.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner052_release_artifact.py >/dev/null

test-learner052: learner052
	mkdir -p validation/learner052
	$(PYTHONPATH_ENV) $(PYTHON) -m unittest discover -s tests -v 2>&1 | $(PYTHONPATH_ENV) $(PYTHON) tools/verify_learner052_clean_rebuild.py --canonicalize-test-log validation/learner052/tests.txt

validate-learner052-core: test-learner052
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner052_validation.py

clean-rebuild-learner052: validate-learner052-core
	$(PYTHONPATH_ENV) $(PYTHON) tools/verify_learner052_clean_rebuild.py

validate-learner052: validate-learner052-core clean-rebuild-learner052
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner052_validation.py --include-clean

package-learner052: validate-learner052
	$(PYTHONPATH_ENV) $(PYTHON) tools/package_learner052_release.py

clean-learner052:
	rm -rf build examples/learner052/promotion_store validation/learner052
	rm -f examples/learner052/promotion_authority.tmg examples/learner052/promotion_authority.tmg.compile.json
	rm -f examples/learner052/learner052_release_artifact.tmg examples/learner052/learner052_release_artifact.tmg.compile.json
	rm -f checksums/PACKAGE_MANIFEST.json checksums/SHA256SUMS.txt
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# TOM Learner 0.2 / World & Query Kernel 0.6 finite family registry.
# Capability expansion is permitted only after the CODEX 0.5.2 kernel repairs
# and the parent-bound promotion authority are revalidated.
.PHONY: learner06 test-learner06 validate-learner06-core clean-rebuild-learner06 validate-learner06 validate-learner06-replay package-learner06 clean-learner06

learner06: build/tomagi-c
	mkdir -p validation/learner06 examples/learner06
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner06_authority.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_learner06_release_artifact.py >/dev/null
	$(PYTHONPATH_ENV) $(PYTHON) tools/build_kernel06_validation_handoff.py >/dev/null

test-learner06: learner06
	mkdir -p validation/learner06
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner06_tests.py

validate-learner06-core: test-learner06
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner06_validation.py

clean-rebuild-learner06: validate-learner06-core
	$(PYTHONPATH_ENV) $(PYTHON) tools/verify_learner06_clean_rebuild.py

validate-learner06: validate-learner06-core clean-rebuild-learner06
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner06_validation.py --include-clean

# Replay validation deliberately excludes recursive clean-build/package steps.
validate-learner06-replay: test-learner06
	$(PYTHONPATH_ENV) $(PYTHON) tools/run_learner06_validation.py

package-learner06: validate-learner06
	$(PYTHONPATH_ENV) $(PYTHON) tools/package_learner06_release.py

clean-learner06:
	rm -rf build examples/learner06/promotion_store validation/learner06
	rm -f examples/learner06/learner06_family_authority.result.json
	rm -f examples/learner06/learner06_family_authority.tmg examples/learner06/learner06_family_authority.tmg.compile.json
	rm -f examples/learner06/learner06_promotion_authority.tmg examples/learner06/learner06_promotion_authority.tmg.compile.json
	rm -f examples/learner06/learner06_release_artifact.tmg examples/learner06/learner06_release_artifact.tmg.compile.json
	rm -f examples/learner06/kernel06_validation_handoff.tmg examples/learner06/kernel06_validation_handoff.tmg.compile.json
	rm -f checksums/PACKAGE_MANIFEST.json checksums/SHA256SUMS.txt
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

.PHONY: test validate demo clean

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

validate: test
	PYTHONPATH=src python benchmarks/run_validation.py
	PYTHONPATH=src python tools/fuzz_parser.py

demo:
	PYTHONPATH=src python examples/feature_ccd_demo.py

clean:
	rm -rf build dist .pytest_cache src/*.egg-info

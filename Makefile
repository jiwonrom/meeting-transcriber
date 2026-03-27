.PHONY: setup test lint typecheck build clean icon

setup:
	pip install -e ".[dev]" --break-system-packages
	@echo "📥 Downloading whisper.cpp small model..."
	mkdir -p ~/.meeting_transcriber/models
	@if [ ! -f ~/.meeting_transcriber/models/ggml-small.bin ]; then \
		curl -L -o ~/.meeting_transcriber/models/ggml-small.bin \
		https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin; \
	fi
	@echo "✅ Setup complete"

test:
	pytest tests/ -x --tb=short -v

lint:
	ruff check src/ tests/ --fix
	ruff format src/ tests/

typecheck:
	mypy src/ --ignore-missing-imports

icon:
	python scripts/generate_icon.py
	@echo "✅ AppIcon.icns generated in resources/"

build: icon
	python setup.py py2app
	@echo "✅ App bundle created in dist/"

dmg: build
	create-dmg \
		--volname "Scribe" \
		--window-size 600 400 \
		--icon-size 100 \
		--app-drop-link 450 200 \
		"dist/Scribe.dmg" \
		"dist/Scribe.app"

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

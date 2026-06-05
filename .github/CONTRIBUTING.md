# Contributing to Distilmark

Thanks for your interest in Distilmark! This is a small, focused project — contributions of any size are welcome, from typo fixes to new conversion engines.

## Ways to contribute

- **Report a bug** — open an [issue](https://github.com/Hesamsamani/pymupdfgui/issues) with steps to reproduce, the PDF you tested with (if shareable), and your OS / Python version.
- **Suggest a feature** — open an issue describing the use case. Concrete examples (a PDF + desired Markdown output) are very helpful.
- **Send a pull request** — bug fixes, new engines, UI polish, docs, translations, all welcome.

## Development setup

```bash
git clone https://github.com/Hesamsamani/pymupdfgui.git
cd pymupdfgui
pip install -r requirements.txt
python -m distilmark
```

For Windows `.exe` builds the release workflow at `.github/workflows/release.yml` is the source of truth — you can reproduce it locally with `pyinstaller` if needed.

## Pull request guidelines

- **Keep PRs focused.** One logical change per PR is much easier to review than a sweeping refactor.
- **Match the existing style.** No new linters or formatters added in a PR unless that's the PR's whole point.
- **Test the golden path.** If you touch the GUI, actually run the app and exercise the feature. If you touch a converter, run it against at least one real PDF.
- **Update `distilmark/_version.py`** if your change is user-facing; bump the patch number for fixes, minor for features.
- **No giant binaries.** Don't commit large PDFs, exported `.exe`s, or screenshot bursts — link to them in the PR description instead.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md). By participating you agree to abide by its terms.

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see [LICENSE](../LICENSE)).

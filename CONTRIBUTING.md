Contributing to EyeON

Thank you for considering contributing to our project! We appreciate your help.

## Reporting Issues

1. If you find a bug or have a feature request, please [open a new issue](https://github.com/LLNL/EyeON/issues) and provide detailed information about the problem.
2. If you find security issues or vulnerabilities, please [report here](https://github.com/LLNL/EyeON/security)

## Making Contributions

We welcome contributions from the community. To contribute to this project, follow these steps:

1. Fork the repository on GitHub.
2. Clone your forked repository to your local machine.
3. We are using pre-commit hooks to adhere to coding standards. Pre-commit is a part of the optional dependencies--see below on how to install. The hooks will run automatically each time a commit is made. If any hook fails, the issues will need to be fixed before committing again.

All contributions to EyeON are made under the MIT license (MIT).

### For Developers:

1. Create a virtual environment with python >= 3.8 [Optional, but recommended]

```bash
python -m venv venv
source venv/bin/activate
```

2. Clone peyeon

```bash
git clone git@github.com:LLNL/pEyeON.git
cd pEyeON
```

3. Install in editable mode
```bash
pip install -e .
```

4. Optional dependencies needed for running pre-commit and building Sphinx documentation: 
```bash
pip install -e ".[dev,docs]"
```

To check that pre-commit install worked, run
```bash
pre-commit install
```
It should return
```bash
pre-commit installed at .git/hooks/pre-commit
```

## Code of Conduct

All participants in the EyeON community are expected to follow our [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct.html).

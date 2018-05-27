# Boa

Conference registration and abstract submission management. Creates Book of Abstract as pdf (LaTeX) and online (HTML) version.

### Requirements

- Python 2/3
- LaTeX, e.g. [texlive](https://tug.org/texlive/)
- [pandoc](http://pandoc.org/)
- imagemagick

Python and imagemagick are probably already installed on your server. LaTeX and pandoc may be installed without root access in your `$HOME` directory.

### Installation

Required Python packages can be installed using `pip install <package>`. Depending on your webserver setup you might need to add the `--user` flag (behind `install`) or want to consider using a [Python virtual environment](https://docs.python.org/3/tutorial/venv.html)

- Install required Python packages.

```bash
pip install future flask sqlalchemy Flask-WTF Flask-Caching
```

- Download Boa

```bash
git clone https://github.com/chstem/Boa.git
```

- Set up Boa environment variables (add to your `.profile` or `.bashrc` files):

```bash
export PATH=$HOME/Boa:$PATH
export PYTHONPATH=$HOME/Boa:$PYTHONPATH
```

- Install optional Python packages as required

```bash
pip install MySQL-python    # Python2
pip install mysqlclient     # Python3
pip install matplotlib      # used by components/feedback, if installed
pip install frozen_flask    # used to export a static version of BoA_online
```

### Basic Configuration

- Create a new folder for your conference and use `Boa.py` to initialize configuration

```bash
mkdir myconference
cd myconference
Boa.py init files
```

- Edit `myconference/preferences/config.py` as required. Most importantly: set up the database configuration!
- To create the database tables run

```bash
Boa.py init database
```

- Further configuration files are located in `Boa/preferences`. All settings can overwritten creating the appropriate files in `myconference/preferences`. Similar email and HTML templates can be copied and customized.

- To start server in development/testing mode run

```bash
Boa.py test
```

For further details please refere to the [Wiki](https://github.com/chstem/Boa/wiki).


### Deployment

For production mode the app should be deployed to a WSGI server. See [Flask documentation](http://flask.pocoo.org/docs/1.0/deploying/) for more details.

What you essentially need to do, is to import the `app` object from the `Boa` module. Make sure your instance directory (`myconference`) is the current working directory during the Python import.


### License

Licensed under GNU GPLv3

Copyright (C) 2018, Christian Stemmle

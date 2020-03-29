pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'hangouts_gtk')

# Modules
python = import('python')

# Module objects
py_installation = python.find_installation(
#	modules: ['hangups', 'giofile']
)

# Make sure Python is installed and found
if not py_installation.found()
	error('No valid python3 binary found')
endif

# Constants
conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'hangouts-gtk.in',
  output: 'hangouts-gtk',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)


install_subdir(
	'widgets',
	install_dir: moduledir
)

install_subdir(
	'backend',
	install_dir: moduledir
)

hangouts_gtk_sources = [
  '__init__.py',
  'main.py',
  'main_window.py',
  'login_window.py'
]

install_data(hangouts_gtk_sources, install_dir: moduledir)

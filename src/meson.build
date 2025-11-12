pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'assets'
gnome = import('gnome')

subdir('blp')

gnome.compile_resources('assets',
  'assets.gresource.xml',
  gresource_bundle: true,
  dependencies: blueprints,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'assets.in',
  output: 'assets',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

assets_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'yahoo_request.py',
  'fred_request.py',
  'node.py',
  'node_library.py',
  'node_dialogs.py',
  'graph_io.py',
  'output_panel.py',
]

install_data(assets_sources, install_dir: moduledir)

desktop_output = []

# Translate and install desktop file
desktop_file = i18n.merge_file(
  input: 'com.dosch.HangoutsGTK.desktop.in',
  output: 'com.dosch.HangoutsGTK.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)
desktop_output += desktop_file

# Translate and install autostart desktop file
autostart_file = i18n.merge_file(
  input: 'com.dosch.HangoutsGTK-autostart.desktop.in',
  output: 'com.dosch.HangoutsGTK-autostart.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)
desktop_output += autostart_file

# Validate desktop files
foreach desktop_file: desktop_output
  desktop_utils = find_program('desktop-file-validate', required: false)
  if desktop_utils.found()
    test('Validate desktop file', desktop_utils,
      args: [desktop_file]
    )
  endif
endforeach

# Translate and install appdata file
appstream_file = i18n.merge_file(
  input: 'com.dosch.HangoutsGTK.appdata.xml.in',
  output: 'com.dosch.HangoutsGTK.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'appdata')
)

# Validate appdata file
appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', appstream_file]
  )
endif

# Install gschema file
install_data('com.dosch.HangoutsGTK.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

# Compile schemas
compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

# Compile resources
gnome = import('gnome')
gnome.compile_resources('hangouts-gtk',
  'hangouts_gtk.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

# Install icon
install_data(
    join_paths('icons', 'com.dosch.HangoutsGTK.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons', 'hicolor', 'scalable', 'apps')
)

# Install DBus service
service_conf = configuration_data()
service_conf.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))

configure_file(
  input: 'com.dosch.HangoutsGTK.service.in',
  output: 'com.dosch.HangoutsGTK.service',
  configuration: service_conf,
  install: true,
  install_dir: dbus_services_dir
)

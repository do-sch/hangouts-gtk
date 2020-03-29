project('hangouts-gtk',
          version: '0.1.0',
    meson_version: '>= 0.51.0',
  default_options: [ 'warning_level=2',
                   ],
)

# import modules
i18n = import('i18n')

# Dependencies
dependency('gtk+-3.0', version: '>=3.24')
dependency('libhandy-0.0', version: '>=0.0.13')
dependency('webkit2gtk-4.0', version: '>=2.24')

subdir('data')
subdir('src')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')

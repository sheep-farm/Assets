python = import('python').find_installation('python3')
fs = import('fs')

# Lê o arquivo wheels_base.txt (apenas dependências essenciais)
wheels_file = join_paths(meson.current_source_dir(), '..', 'wheels_base.txt')
wheels_content = fs.read(wheels_file)

# Remove aspas simples, vírgulas, comentários e quebras de linha
wheels_lines = wheels_content.strip().split('\n')
wheels = []
foreach line : wheels_lines
  # Remove espaços em branco
  trimmed = line.strip()
  # Ignora comentários e linhas vazias
  if trimmed != '' and not trimmed.startswith('#')
    # Remove aspas e vírgulas
    wheel = trimmed.replace('\'', '').replace(',', '')
    wheels += [wheel]
  endif
endforeach

wheels_dir = meson.current_source_dir()
wheel_paths = []
foreach w : wheels
  wheel_paths += [join_paths(wheels_dir, w)]
endforeach

wheels_str = ' '.join(wheel_paths)

# Instala apenas dependências base no Flatpak
# Dependências por projeto serão instaladas automaticamente via project_dependencies.py
meson.add_install_script(
  'sh', '-c',
  'pip3 install --upgrade --no-deps --target="$MESON_INSTALL_DESTDIR_PREFIX/lib/python3.12/site-packages" --no-cache-dir ' + wheels_str + ' && ' +
  'find "$MESON_INSTALL_DESTDIR_PREFIX" -type d -name tests -exec rm -rf {} + || true'
)
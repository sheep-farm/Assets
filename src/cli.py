#!/usr/bin/env python3
"""
cli.py - Interface de linha de comando para gerenciar projetos .assets

Uso:
    python -m src.cli add-deps <project.assets> <package1> [package2 ...]
    python -m src.cli list-deps <project.assets>
    python -m src.cli migrate <old.assets> <new.assets>
    python -m src.cli create <new.assets>
"""

import sys
import argparse
from pathlib import Path


def cmd_add_deps(args):
    """Adiciona dependências a um projeto"""
    from .dependency_manager import add_dependencies_to_project

    project_path = args.project
    packages = args.packages

    if not Path(project_path).exists():
        print(f"❌ Projeto não encontrado: {project_path}")
        return 1

    print(f"📦 Adicionando dependências ao projeto: {project_path}")
    print(f"Pacotes: {', '.join(packages)}\n")

    success = add_dependencies_to_project(project_path, packages)

    return 0 if success else 1


def cmd_add_wheels(args):
    """Adiciona wheels de um diretório ao projeto"""
    from .zip_project import AssetsProject

    project_path = args.project
    wheels_dir = Path(args.wheels_dir)

    if not Path(project_path).exists():
        print(f"❌ Projeto não encontrado: {project_path}")
        return 1

    if not wheels_dir.exists() or not wheels_dir.is_dir():
        print(f"❌ Diretório de wheels não encontrado: {wheels_dir}")
        return 1

    # Coletar todos os wheels no diretório
    wheel_files = list(wheels_dir.glob("*.whl"))

    if not wheel_files:
        print(f"❌ Nenhum wheel encontrado em: {wheels_dir}")
        return 1

    print(f"\n{'='*60}")
    print(f"📦 ADICIONANDO WHEELS AO PROJETO")
    print(f"{'='*60}")
    print(f"Projeto: {Path(project_path).name}")
    print(f"Diretório: {wheels_dir}")
    print(f"Wheels encontrados: {len(wheel_files)}")
    print()

    for whl in wheel_files:
        print(f"  • {whl.name}")

    print()

    # Carregar projeto e adicionar wheels
    project = AssetsProject(project_path)
    graph_data = project.load_graph()

    if graph_data is None:
        print(f"❌ Não foi possível carregar projeto")
        return 1

    success = project.save_graph(graph_data, wheel_files)

    if success:
        print()
        print(f"{'='*60}")
        print(f"✓ WHEELS ADICIONADOS COM SUCESSO")
        print(f"{'='*60}\n")

    return 0 if success else 1


def cmd_list_deps(args):
    """Lista dependências de um projeto"""
    from .zip_project import AssetsProject

    project_path = args.project

    if not Path(project_path).exists():
        print(f"❌ Projeto não encontrado: {project_path}")
        return 1

    project = AssetsProject(project_path)
    wheels = project.list_wheels()

    print(f"\n{'='*60}")
    print(f"📦 DEPENDÊNCIAS DO PROJETO")
    print(f"{'='*60}")
    print(f"Projeto: {Path(project_path).name}")
    print()

    if wheels:
        print(f"Wheels incluídos ({len(wheels)}):")
        for wheel in wheels:
            print(f"  • {wheel}")
    else:
        print("Nenhum wheel encontrado no projeto")

    print(f"{'='*60}\n")

    return 0


def cmd_migrate(args):
    """Migra projeto antigo (JSON) para novo formato (ZIP)"""
    from .zip_project import migrate_old_project

    old_path = args.old_project
    new_path = args.new_project

    if not Path(old_path).exists():
        print(f"❌ Projeto antigo não encontrado: {old_path}")
        return 1

    if Path(new_path).exists() and not args.force:
        print(f"❌ Projeto já existe: {new_path}")
        print(f"Use --force para sobrescrever")
        return 1

    print(f"🔄 Migrando projeto...")
    print(f"  Origem: {old_path}")
    print(f"  Destino: {new_path}\n")

    success = migrate_old_project(old_path, new_path)

    return 0 if success else 1


def cmd_create(args):
    """Cria novo projeto vazio"""
    from .zip_project import create_new_project

    project_path = args.project

    if Path(project_path).exists() and not args.force:
        print(f"❌ Projeto já existe: {project_path}")
        print(f"Use --force para sobrescrever")
        return 1

    # Criar grafo vazio
    graph_data = {
        "version": "1.0",
        "nodes": [],
        "connections": [],
        "view_state": {
            "zoom": 1.0,
            "scroll_x": 0,
            "scroll_y": 0
        },
        "project_metadata": {
            "requirements": [],
            "author": "",
            "description": "",
            "created_at": None,
            "modified_at": None,
            "tags": [],
            "version": "1.0.0"
        }
    }

    print(f"📄 Criando novo projeto: {project_path}\n")

    success = create_new_project(project_path, graph_data)

    if success:
        print(f"\n✓ Projeto criado com sucesso!")
        print(f"  Arquivo: {project_path}")

    return 0 if success else 1


def main():
    """Entry point do CLI"""
    parser = argparse.ArgumentParser(
        description="Gerenciador de projetos Assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Adicionar dependências
  python -m src.cli add-deps project.assets pandas numpy matplotlib

  # Listar dependências
  python -m src.cli list-deps project.assets

  # Migrar projeto antigo
  python -m src.cli migrate old_project.assets new_project.assets

  # Criar novo projeto
  python -m src.cli create my_project.assets
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Comando a executar')
    subparsers.required = True

    # Comando: add-deps
    parser_add = subparsers.add_parser('add-deps', help='Adiciona dependências ao projeto')
    parser_add.add_argument('project', help='Caminho do projeto .assets')
    parser_add.add_argument('packages', nargs='+', help='Pacotes a adicionar')
    parser_add.set_defaults(func=cmd_add_deps)

    # Comando: add-wheels
    parser_wheels = subparsers.add_parser('add-wheels', help='Adiciona wheels de um diretório ao projeto')
    parser_wheels.add_argument('project', help='Caminho do projeto .assets')
    parser_wheels.add_argument('wheels_dir', help='Diretório contendo arquivos .whl')
    parser_wheels.set_defaults(func=cmd_add_wheels)

    # Comando: list-deps
    parser_list = subparsers.add_parser('list-deps', help='Lista dependências do projeto')
    parser_list.add_argument('project', help='Caminho do projeto .assets')
    parser_list.set_defaults(func=cmd_list_deps)

    # Comando: migrate
    parser_migrate = subparsers.add_parser('migrate', help='Migra projeto antigo para novo formato')
    parser_migrate.add_argument('old_project', help='Caminho do projeto antigo (.assets JSON)')
    parser_migrate.add_argument('new_project', help='Caminho do novo projeto (.assets ZIP)')
    parser_migrate.add_argument('--force', action='store_true', help='Sobrescrever se já existir')
    parser_migrate.set_defaults(func=cmd_migrate)

    # Comando: create
    parser_create = subparsers.add_parser('create', help='Cria novo projeto vazio')
    parser_create.add_argument('project', help='Caminho do novo projeto .assets')
    parser_create.add_argument('--force', action='store_true', help='Sobrescrever se já existir')
    parser_create.set_defaults(func=cmd_create)

    # Parse argumentos
    args = parser.parse_args()

    # Executar comando
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
        return 130
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

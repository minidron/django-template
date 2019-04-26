from {{ cookiecutter.project_name }}.libs.fabric_utils.fabric_class import (
    add_class_methods_as_functions,
    DjangoFabric
)


class Fabric(DjangoFabric):
    host = '{{ cookiecutter.production_host }}'
    app_name = '{{ cookiecutter.project_name }}'
    repository = '{{ cookiecutter.git_repository }}'
    remote_db_name = '{{ cookiecutter.project_name }}'
    local_db_name = '{{ cookiecutter.local_db_name }}'
    use_yarn = True


__all__ = add_class_methods_as_functions(Fabric(), __name__)

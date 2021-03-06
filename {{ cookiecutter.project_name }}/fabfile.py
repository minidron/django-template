from fabric_class import add_class_methods_as_functions, DjangoFabric


class Fabric(DjangoFabric):
    app_name = '{{ cookiecutter.project_name }}'
    host = '{{ cookiecutter.production_host }}'
    local_db_name = '{{ cookiecutter.local_db_name }}'
    remote_db_name = '{{ cookiecutter.project_name }}'
    repository = '{{ cookiecutter.git_repository }}'
    use_yarn = True


__all__ = add_class_methods_as_functions(Fabric(), __name__)

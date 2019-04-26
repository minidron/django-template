# --coding: utf8--
u"""
Модуль позволяет:
    1) записывать функции для библиотеки fabric в виде классов
    2) функциональная утилита `add_class_methods_as_functions`
       преобразует методы класса, начинающиеся с `fab_` в
       обычные функции, которые уже использует fabric
Пример использования:
    from kupola.fabric_class import DjangoFabric,\
    add_class_methods_as_functions
    class MyFabricClass(DjangoFabric):
        # например перегрузим метод получения пути к
        # локальному виртуальному окружению
        def get_local_venv_path(self):
            return '~/.Envs'
    # в конце fabfile вызываем функцию
    # `add_class_methods_as_functions`
    # и инициализируем наш класс `MyFabricClass`
    __all__ = add_class_methods_as_functions(MyFabricClass(
        app_name='my_app',
        db_name='my_db_name',
        base_path='/bash/path/remote/server/',
        repository='git@github.com/my_app.git',
        revision='dev',
        skip_tests=False,
        skip_db_dump=False,
    ), __name__)
"""
import time
import os.path
import inspect
import sys
from pprint import pprint

from fabric.api import run, prefix, sudo, local, lcd, get, env
from fabric.contrib.files import exists
from fabric.context_managers import settings
# from fabric.decorators import hosts


class BaseFabric(object):
    hosts = []
    host = ''
    app_name = None
    user = 'mini'

    remote_base_path = '/var/venv/'
    remote_project_path = None
    remote_venv_path = None

    local_project_path = None
    local_venv_path = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if not env.host_string:
            env.host_string = self.host
        env.user = self.user
        # if not env.hosts:
        #     env.hosts = self.hosts

    def get_app_name(self):
        return self.app_name

    def get_remote_venv_path(self):
        """
        Путь к удаленному виртуальному окружению.
        """
        if self.remote_venv_path:
            return self.remote_venv_path
        return '{}{}'.format(self.remote_base_path, self.get_app_name())

    def get_remote_project_path(self):
        """
        Путь к удаленному каталогу с проектом.
        """
        if self.remote_project_path:
            return self.remote_project_path
        return os.path.join(self.get_remote_venv_path(), 'src')

    def get_local_venv_path(self):
        """
        Путь к локальному виртуальному окружению.
        """
        if self.local_venv_path:
            return self.local_venv_path
        return os.path.dirname(self.get_local_project_path())

    def get_local_project_path(self):
        """
        Путь к локальному каталогу с проектом.
        """
        if self.local_project_path:
            return self.local_project_path
        fab_module = sys.modules[self.__class__.__module__]
        return os.path.dirname(os.path.abspath(fab_module.__file__))

    def remote_venv(self):
        """
        Активировать виртуальное окружение на удаленном сервере.
        """
        return prefix('cd {0} && source {1}/bin/activate'.format(
            self.get_remote_project_path(),
            self.get_remote_venv_path()))

    def fab_del_pyc(self):
        """
        Очистить локальный кеш Python.
        """
        local('find -name \*.pyc -delete')

    def fab_remote_del_pyc(self):
        """
        Очистить удаленный кеш Python.
        """
        run("find {0} -name '*.pyc' -delete".format(
            self.get_remote_project_path()))


class DjangoFabric(BaseFabric):
    repository = None
    revision = 'master'

    skip_tests = False
    skip_db_dump = False

    remote_db_name = None
    local_db_name = None

    remote_backups_path = None
    local_backups_path = None

    pip_force_upgrade = False

    remote_django_settings = None

    use_yarn = False

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        super(DjangoFabric, self).__init__(**kwargs)

    def fab_ipnb(self):
        """
        Launch IPython Notebook server on the remote machine.
        """
        self.fab_remote_manage('shell_plus --notebook')

    def get_remote_backups_path(self):
        if self.remote_backups_path:
            return self.remote_backups_path
        return '/var/backups/{0}'.format(self.get_app_name())

    def get_local_backups_path(self):
        if self.local_backups_path:
            return self.local_backups_path
        return '~/{0}-backups'.format(self.get_app_name())

    def get_db_backup_filename(self):
        return os.path.join(
            self.get_remote_backups_path(),
            '{0}-{1}.sql'.format(
                self.get_app_name(),
                time.strftime('%Y-%m-%d.%H-%M-%S')
            )
        )

    def get_local_db_name(self):
        """
            Получить имя локальной базы данных.
        """
        if self.local_db_name:
            return self.local_db_name
        else:
            return self.get_remote_db_name()

    def get_remote_db_name(self):
        """
        Получить имя удаленной базы, если не указано явно
        пробует получить имя из настроек Django.
        """
        if self.remote_db_name:
            return self.remote_db_name
        else:
            if not self.remote_django_settings:
                self.remote_django_settings = self.get_remote_django_settings()
            try:
                return self.remote_django_settings.DATABASES['default']['name']
            except (KeyError, AttributeError):
                return self.remote_db_name

    def get_remote_django_settings(self):
        """
        Настройки удаленного Django-проекта.
        """
        if not hasattr(self, '_django_settings'):
            output = self.fab_remote_manage('diffsettings 2>/dev/null')

            class Config(object):
                pass

            config = Config()
            lines = output.splitlines()
            for line in lines:
                try:
                    exec('config.%s' % line)
                except SyntaxError:
                    continue
            self._django_settings = config
        return self._django_settings

    def fab_remote_django_settings(self):
        """
            Вывести на экран настройки django с удаленного хоста.
        """
        if not self.remote_django_settings:
            self.remote_django_settings = self.get_remote_django_settings()
        if self.remote_django_settings:
            pprint(self.remote_django_settings.__dict__)
        else:
            print('django_settings miss')

    def fab_remote_manage(self, cmd):
        """
            Выполнить 'python manage.py cmd' на удалённом сервере.
        """
        with self.remote_venv():
            return run('python manage.py %s' % cmd)

    def manage(self, cmd):
        """
            Выполнить 'python manage.py cmd' локально.
        """
        with lcd(self.get_local_project_path()):
            local(('python manage.py {0}'.format(cmd)))

    def fab_remote_update_repository(self):
        """
            Обновить код в удаленном репозитории.
        """
        with self.remote_venv():
            sudo('chown -R www-data:adm {0}'.format('.git/'))
            sudo('chmod -R 770 {0}'.format('.git/'))
            run('git checkout --force {0}'.format(self.revision))
            run('git pull origin {0}'.format(self.revision))

    def fab_deploy(self):
        """
            Деплой на сервер
        """
        if not self.skip_tests:
            self.fab_test()

        self.remote_create_project_paths()
        self.remote_clone_repository()

        if not self.skip_db_dump:
            self.fab_remote_dumpdb()

        self.fab_push()
        self.fab_remote_update_repository()
        self.fab_remote_del_pyc()
        self.fab_remote_pip()
        self.fab_link_local_settings()
        self.fab_remote_manage('migrate')
        if self.use_yarn:
            self.fab_remote_manage('yarn install')
        self.fab_remote_manage('collectstatic --noinput')
        sudo('touch {0}/reload.me'.format(self.get_remote_venv_path()))
        self.clear_pagespeed_cache()

    def fab_link_local_settings(self):
        """
            Создать ссылку на файл локальных настроек.
        """
        with self.remote_venv():
            run(('ln -fs ../../../local_settings.py '
                '{0}/settings/local.py').format(self.app_name))

    def fab_remote_pip_whell(self):
        """
            Установка пакетов в виртуальное окружение.
            Из-за того что мы использем ключи к git lab
            а иногда требуется устанавливать с sudo
            пакеты ставим с промежуточным скачиванием в tmp
            используя wheel, которая идет с pip-tolls
            убедитесь что pip-tolls установлен
            pip wheel --wheel-dir=/tmp/wheelhouse SomePackage
            pip install --no-index --find-links=/tmp/wheelhouse SomePackage
        """
        tmp_wheel_dir = "/tmp/whl_{}".format(self.app_name)

        with self.remote_venv():
            pip_opts = '--upgrade' if self.pip_force_upgrade else ''
            run('pip wheel --wheel-dir {} {} -r requirements.txt'.format(
                tmp_wheel_dir,
                pip_opts
                ))
        sudo('{}/bin/pip install --force-reinstall --ignore-installed\
         --upgrade --no-index --no-deps {}/*'.format(
            self.get_remote_venv_path(),
            tmp_wheel_dir
        ))
        sudo('rm -rf {}'.format(tmp_wheel_dir))

    def fab_remote_pip(self):
        with self.remote_venv():
            pip_opts = '--upgrade' if self.pip_force_upgrade else ''
            run('pip install {} -r requirements.txt'.format(pip_opts))

    def clear_pagespeed_cache(self):
        sudo('rm -rf /var/cache/ngx_pagespeed_cache/*')
        sudo('systemctl restart nginx')

    def remote_create_project_paths(self):
        pp = self.get_remote_project_path()

        if not exists('{0}'.format(pp), use_sudo=True):
            sudo('mkdir -p {0}'.format(pp))
            sudo('chown -R www-data:www-data {0}'.format(pp))
            sudo('chmod -R g+w {0}'.format(pp))

    def remote_clone_repository(self):
        """
            Проверка/клонирование основного репозитория проекта.
        """
        if not exists('{0}/.git'.format(self.get_remote_project_path()),
                      use_sudo=True):
            run('git clone {0} {1}'.format(
                self.repository,
                self.get_remote_project_path()))

    def fab_push(self):
        """
            Отправить изменения из локального репозитория в основной.
        """
        local('git push origin {0}'.format(self.revision))

    def fab_remote_create_backups_dir(self):
        """
            Создать каталог для резервных копий на удаленном сервере.
        """
        sudo('mkdir -p {0}'.format(self.get_remote_backups_path()))

    def fab_remote_dumpdb(self):
        """
            Снять копию базы на удаленном сервере.
        """
        self.fab_remote_create_backups_dir()
        backup_name = self.get_db_backup_filename()
        sudo('sudo -u postgres pg_dump -c {0} > {1}'.format(
            self.get_remote_db_name(), backup_name))
        return backup_name

    def dumpdata(self, apps=''):
        """
        ```manage.py dumpdata``` wrapper using pretty-printed YAML.
        """
        self.manage('dumpdata --format=yaml-pretty {0}'.format(apps))

    def fab_backup(self):
        """
            Слить копию боевого сервера на локальную машину.
        """
        self.fab_remote_dumpdb()
        local('mkdir -p %s' % self.get_local_backups_path())

        with settings(warn_only=True):
            local('rsync -rlv -e ssh %s:%s %s' % (
                env.host, self.get_remote_backups_path(),
                self.get_local_backups_path()))

        media_path = os.path.join(self.get_remote_project_path(), 'media')
        local_media_path = os.path.join(self.get_local_backups_path(),
                                        'media')
        with settings(warn_only=True):
            local('rsync --exclude "CACHE" -rlv -e ssh %s:%s %s' % (
                env.host, media_path, local_media_path))
        # ? sudo('rm %s' % self.db_backup)

    def fab_syncmedia(self):
        """
            Слить медиа файлы с удаленного сервера в текущую локальную копию.
        """
        media_path = os.path.join(self.get_remote_project_path(), 'media')
        lp = self.get_local_project_path()
        local('rsync --exclude "CACHE" -rlv -e ssh %s:%s %s' % (
            env.host_string, media_path, lp))
        local('sudo chown -R www-data:www-data {0}/media'.format(lp))
        local('sudo chmod -R g+w %s/media' % lp)

    def fab_syncdb(self, local_db_name=None):
        """
            Слить базу с удаленного сервера в текущую локальную копию.
        """
        backup_name = self.fab_remote_dumpdb()
        if local_db_name is None:
            local_db_name = self.get_local_db_name()
        get(backup_name, '/tmp/to.sql')
        local('sudo sudo -u postgres psql %s < /tmp/to.sql' % local_db_name)
        local('rm /tmp/to.sql')
        self.fab_del_pyc()
        self.manage('migrate')

    def fab_syncdata(self):
        """
        Слить базу и файлы с удаленного сервера в текущую локальную копию.
        """
        self.fab_syncmedia()
        self.fab_syncdb()

    def fab_test(self, apps=''):
        """
            Прогнать тесты на локальной машине.
        """
        self.manage('test %s' % apps)

    def fab_tags(self):
        """
            Сгенерировать файл ctags.
        """
        with lcd(self.get_local_venv_path()):
            local('ctags -f ctags -R lib/python2.7/site-packages '
                  'src/%s' % self.get_app_name())

    def fab_pip(self):
        """
            pip install -r requirements/dev.txt
        """
        local('pip install -r requirements/dev.txt')


def add_class_methods_as_functions(instance, module_name):
    '''
    Utility to take the methods with prefix 'fab_' of the class instance,
    and add them as functions to a module `module_name`, so that Fabric
    can find and call them. Call this at the bottom of a module after
    the class definition. Returns a list of method for __all__ variable,
    otherwise command 'fab -l' will show extra commands.
    '''
    # get the module as an object
    module_obj = sys.modules[module_name]
    method_names_list = []

    # Iterate over the methods of the class and dynamically create a function
    # for each method that calls the method and add it to the current module
    for method in inspect.getmembers(instance, predicate=inspect.ismethod):
        method_name = method[0]

        if method_name.startswith('fab_'):
            # get the bound method
            func = getattr(instance, method_name)

            method_name = method_name.replace('fab_', '')

            # add the function to the current module
            setattr(module_obj, method_name, func)
            method_names_list += [method_name]

    return method_names_list

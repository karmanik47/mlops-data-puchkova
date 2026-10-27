# Отчёт по практической работе № 3

## 1. Окружение

Работа выполнена 27 октября 2026 года в отдельном Git-репозитории
`mlops-data-puchkova`, основная ветка — `main`.

| Компонент | Зафиксированная версия |
|---|---:|
| Python | 3.12.14 |
| Poetry | 2.5.1 |
| DVC | 3.63.0 |
| ClearML | 2.1.3 |
| scikit-learn | 1.8.0 |
| pandas | 3.0.1 |
| pathspec | 0.12.1 |

Версии прямых зависимостей закреплены в `pyproject.toml`, полное разрешение —
в `poetry.lock`. `pathspec` закреплён явно, потому что DVC 3.63.0 использует
API, удалённый в pathspec 1.x.

Репозиторий: `C:\Users\user\Desktop\mloops\mlops-data-puchkova`.
Удалённый Git-сервер в доступном окружении не настроен, поэтому ссылка пока
локальная.

## 2. Подготовка и проверка таблиц

`prepare_data.py` поддерживает режимы `base`, `wine` и `iris_features`.
Перед записью строки стабильно сортируются по всем исходным столбцам, индекс
pandas не сохраняется, окончания строк и формат чисел заданы явно.

Повторный запуск `base` дал одинаковые байты:

```text
deterministic=True
iris.csv SHA-256 = 6d700503c9c2e2c71d187b889a87af8a8d3a6dd5bae1266d46f4ee4db5a6349f
```

`check_data.py` проверяет точный состав состояния, отсутствие безымянного
индекса и пропусков, число строк, порядок столбцов, исходные значения и
вычисляемые признаки с числовым допуском `1e-9`. Он завершился успешно для
`base`, `wine`, `iris_features` и итогового `merged`.

## 3. Версии DVC и Git

Настроен DVC merge driver:

```text
*.dvc merge=dvc
dvc git-hook merge-driver --ancestor %O --our %A --their %B
```

| Состояние | Git commit | DVC directory MD5 | Состав |
|---|---|---|---|
| Base (`data-v1`) | `79f10ce344baa18ef02586a82eed146ea723d93e` | `bf5656de288a783265cb7b85509abc8e.dir` | базовый `iris.csv` |
| `feature/wine` | `567c6b51b411ad1ff20acfee1d4e36c4c5a3ea75` | `f8fe844935c3e7d61c8736baacbf1018.dir` | базовый Iris и Wine |
| Iris features до merge | `8b44cb3` | `c6a76d56d42022aa7753d44fd7e84d6a.dir` | Iris с двумя новыми признаками |
| Merge двух ветвей | `f4142c651fda98999c609ea40fad8ca0de6bc4af` | `957c42d7c9ecafed014287db892a5935.dir` | Iris features и Wine |
| Merge в `main` | `6af4d744aac8aeadbcf57cccfde0fb6dc890aad0` | `957c42d7c9ecafed014287db892a5935.dir` | проверенный итог |

Тег `data-v1` указывает на базовый commit
`79f10ce344baa18ef02586a82eed146ea723d93e`.

При переключении с `feature/wine` на `main` команда `dvc checkout` удалила
`wine.csv` и восстановила базовый Iris. SHA-256 Iris до и после переключения
совпал. Затем ветка `feature/iris-features` была создана от `main`.

Слияние `feature/wine` в `feature/iris-features` прошло через DVC merge driver
без маркеров конфликта. После `dvc checkout` итог содержал изменённый Iris из
первой ветви и неизменный Wine из второй. История обеих ветвей сохранена.

## 4. DVC remote и чистое восстановление

Remote `local-storage` расположен отдельно от Git-репозитория:

```text
C:/Users/user/Desktop/mloops/dvc-remote-puchkova
```

В `.dvc/config` находится только безопасный путь; credentials отсутствуют.
Локальные DVC cache и workspace CSV игнорируются Git. Все четыре состояния
данных были отправлены командой `dvc push`.

Для проверки создан новый каталог:

```text
C:\Users\user\Desktop\mloops\mlops-data-puchkova-clean-clone
```

Он получен командой `git clone`, без копирования workspace и старого cache.
`dvc pull` сообщил `3 files fetched and 2 files added`, после чего
`python check_data.py merged` успешно проверил обе таблицы.

Итоговые контрольные значения:

| Файл | SHA-256 | Форма |
|---|---|---:|
| `data.dvc` | `96dfda4219f2457ea0fdce7cb7d69cb89dd0e55680d6be9b639f3f5624c1aefb` | метаданные двух файлов |
| `data/iris.csv` | `3e1ba63f55da2aabc432d00b1670140f5162bf9ef34b837598ec2fc176c9ff26` | 150 × 7 |
| `data/wine.csv` | `38860ba04ace4d402242340bcf40be4bd6f4ebde9144a3dc89dc12c20f7f8e60` | 178 × 14 |

В Git нет ни одного CSV, DVC cache или ClearML credential.

## 5. ClearML Dataset

Подготовлен и проверен синтаксически скрипт `clearml_datasets.py`. Он использует
требуемые уникальные имена:

```text
project: MIIT/MLOps/practice_3/puchkova
dataset name: sklearn-tabular-puchkova
```

Скрипт должен создать и финализировать следующую lineage:

```text
1.0.0 (BASE_ID, original Iris)
├── 1.1.0 (WINE_ID, adds wine.csv)
└── 2.0.0 (IRIS_FEATURES_ID, modifies iris.csv)
```

Он создаёт состояния во временных каталогах, поэтому не изменяет DVC workspace,
загружает в дочерние версии только добавленный или изменённый файл, получает
версии строго по ID в три отдельные пустые директории и сохраняет проверку в
игнорируемый `clearml_verification.json`.

На этой машине отсутствуют `clearml.conf`, `CLEARML_API_ACCESS_KEY` и
`CLEARML_API_SECRET_KEY`; доступной авторизованной браузерной сессии также нет.
Поэтому серверные Dataset нельзя честно создать, загрузить и проверить без
выданных сервером credentials. Значения не подделывались:

```text
BASE_ID = NOT_CREATED_NO_CLEARML_CREDENTIALS
WINE_ID = NOT_CREATED_NO_CLEARML_CREDENTIALS
IRIS_FEATURES_ID = NOT_CREATED_NO_CLEARML_CREDENTIALS
```

После настройки SDK серверная часть запускается одной командой:

```powershell
poetry run python .\clearml_datasets.py all
```

Фактические IDs будут записаны в игнорируемый `clearml_ids.json`, а полный
dependency graph, списки `added`/`modified`/`removed`, формы, столбцы и SHA-256
скачанных файлов — в `clearml_verification.json`. После успешного запуска эти
значения нужно перенести в данный раздел отчёта. Созданные Dataset скрипт не
удаляет.

## 6. Сравнение DVC и ClearML Dataset

| Наблюдаемое свойство | DVC | ClearML Dataset |
|---|---|---|
| Идентификатор версии | В работе состояние однозначно задаёт MD5 каталога в `data.dvc`; соответствующий Git commit выбирает этот метафайл. | Конкретную серверную версию должен однозначно задавать Dataset ID; номер `1.0.0` удобен человеку, но не заменяет ID. |
| Расположение метаданных | `data.dvc` хранится в Git. | Метаданные, статус и lineage хранятся на ClearML Server. |
| Расположение файлов | Фактические CSV попали в DVC cache и отдельный `local-storage`, но не в Git. | После `upload()` файлы должны находиться в ClearML File Server или настроенном внешнем storage. |
| Создание дочерней версии | Создана Git-ветка, изменён workspace, повторно выполнен `dvc add`, новый `data.dvc` закоммичен. | Скрипт вызывает `Dataset.create(..., parent_datasets=[BASE_ID])` и добавляет только разницу. |
| Переключение версии | Наблюдение: одного `git switch` было недостаточно; фактические файлы изменились после `dvc checkout`. | Версия выбирается через `Dataset.get(dataset_id=...)`, затем скачивается в отдельный каталог. |
| Чистая машина | Проверено новым clone: `dvc pull` восстановил оба CSV из remote. | Требуются SDK-конфигурация, Dataset ID и доступ к серверному storage; фактическая проверка заблокирована отсутствием credentials. |
| Ветвление | Две Git-ветки вышли из `data-v1` и содержали разные состояния одной DVC-директории. | Планируемые `1.1.0` и `2.0.0` имеют одного parent `BASE_ID`, а не цепочку. |
| Слияние | DVC merge driver объединил Wine и изменённый Iris; итог проверен по содержимому и SHA-256. | ClearML обычно выражает результат новой производной Dataset version и её parents; `finalize()` сам по себе версии не сливает. |
| Связь с Git | Прямая: Git хранит историю `data.dvc`, ветви, merge commit и тег `data-v1`. | Dataset живёт независимо на ClearML Server; связь с Git нужно фиксировать отдельно в задаче или отчёте. |
| UI | Для локального DVC remote отдельный UI не использовался. | ClearML Web UI должен показывать версии, статус Completed и lineage после загрузки. |

## 7. Ответы на контрольные вопросы

1. **Какой объект однозначно определяет версию данных в DVC?**  
   Хэш output в `data.dvc` (`md5` каталога в данной работе) однозначно задаёт
   содержимое версии. Git commit нужен, чтобы выбрать соответствующую версию
   самого `data.dvc` вместе с кодом.

2. **Почему одного Git-коммита недостаточно без DVC remote?**  
   Git-коммит хранит метаданные и хэш, но не байты CSV. Если нужного объекта нет
   ни в локальном cache, ни в доступном remote, восстановить данные по одному
   хэшу нельзя.

3. **Чем Dataset version отличается от Dataset ID в ClearML?**  
   Version — человекочитаемая метка, например `1.1.0`. Dataset ID — уникальный
   серверный идентификатор конкретного объекта версии; для автоматического
   получения следует использовать ID.

4. **Почему `finalize()` нельзя считать созданием следующей версии?**  
   `finalize()` только переводит текущий mutable Dataset в immutable состояние.
   Следующую версию создаёт отдельный `Dataset.create()` с новым version и,
   при необходимости, `parent_datasets`.

5. **Как доказать, что ClearML version `2.0.0` создана от базы, а не от `1.1.0`?**  
   Проверить `get_dependency_graph()` и parent IDs: непосредственным parent
   должен быть `BASE_ID`, а `WINE_ID` не должен находиться среди предков.
   Дополнительно полный состав `2.0.0` не содержит `wine.csv`, а список modified
   содержит `iris.csv`.

6. **Что произойдёт, если после `git switch` не выполнить DVC checkout?**  
   Git переключит `data.dvc`, но workspace может остаться от предыдущей ветки.
   Код и метаданные будут указывать на одну версию, а локальные CSV фактически
   будут другой; `dvc status` покажет расхождение.

7. **Где удобнее DVC, а где ClearML Dataset?**  
   В данной работе DVC удобнее для синхронного ветвления и merge данных вместе
   с Git-кодом. ClearML Dataset удобнее для выдачи отдельного Dataset ID,
   просмотра lineage и состава через UI, а также для использования одной версии
   несколькими экспериментами независимо от Git-ветки.

## 8. Состав сдаваемого репозитория

В Git находятся требуемые `.dvc/config`, `.dvcignore`, `.gitattributes`,
`.gitignore`, `data.dvc`, `prepare_data.py`, `check_data.py`, `pyproject.toml`,
`poetry.lock` и `REPORT.md`. Дополнительно включён `clearml_datasets.py` для
воспроизводимого выполнения серверной части. CSV, `.venv`, DVC cache, remote,
скачанные ClearML-копии и credentials в Git не добавлены.

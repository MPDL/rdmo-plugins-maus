import base64
import json
from functools import partial, reduce

from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

import requests
import yaml

from rdmo.core.imports import handle_fetched_file
from rdmo.core.plugins import get_plugin
from rdmo.projects.imports import RDMOXMLImport
from rdmo.projects.mixins import ProjectImportMixin
from rdmo.projects.models.project import Project
from rdmo.projects.models.value import Value
from rdmo.projects.utils import save_import_snapshot_values, save_import_tasks, save_import_values, save_import_views
from rdmo.questions.models import Catalog

from ..forms.validators import FilePathExtensionValidator
from ..utils import get_optionset_options, get_pages, get_questionsets, groupby_values


class SMPRepoImportMixin(ProjectImportMixin, RDMOXMLImport):
    '''This class is meant for import plugin providers. It enables the import of
    repository metadata (license, authorship, dependencies) as well as
    RDMO xml project files in projects with the Software Management Plan (SMP) catalogue.

    It requires plugins to implement the following methods, which take two arguments (url and headers):
    - get_citation()
    - get_license()
    - get_sbom()
    - get_languages()

    GET_CITATION():
    Args:
    - url: url to a CITATION.cff file in the repository
    - headers: request authorization headers

    Returns the content of the CITATION.cff file (str) or None

    GET_LICENSE():
    Args:
    - url: repository's api endpoint with its license information
    - headers: request authorization headers

    Returns the spdx id of the repository's license (str) or None

    GET_SBOM():
    (sbom stands for software bill of materials)
    Args:
    - url: repository's api endpoint with its dependency information
    - headers: request authorization headers

    Returns a dict with keys 'dependencies' and 'dependency_licenses', and values of type str or None

    GET_LANGUAGES():
    Args:
    - url: repository's api endpoint with its languages
    - headers: request authorization headers

    Returns a list of all repository languages (list[str]) or an empty list

    '''

    import_project = None
    xml_import_plugin = None

    metadata_attr_mapping = {
        'license': 'https://rdmorganiser.github.io/terms/domain/smp/software-license',
        'language': 'https://rdmorganiser.github.io/terms/domain/smp/language',
        'dependencies': 'https://rdmorganiser.github.io/terms/domain/smp/external-components',
        'dependency_licenses': 'https://rdmorganiser.github.io/terms/domain/smp/third-party-licenses',
        'title': 'https://rdmorganiser.github.io/terms/domain/project/title',
        'contributor': {
            'family-names': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/family-name',
            'familyName': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/family-name',
            'given-names': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/given-name',
            'givenName': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/given-name',
            'name': 'https://rdmorganiser.github.io/terms/domain/project/partner/name',
            'orcid': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/orcid',
            'website': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/website',
            'affiliation': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/affiliation',
            'id': 'https://rdmorganiser.github.io/terms/domain/project/partner/id',
            'type': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/type',
            'orcid-autocomplete': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/orcid-autocomplete',
            'role': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/role',
            'ror-id': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/affiliation/ror-id',
            'ror-autocomplete': 'https://rdmo.mpdl.mpg.de/terms/domain/project/partner/affiliation/ror-autocomplete'
        },
        'pid': 'https://rdmorganiser.github.io/terms/domain/smp/software-pid'
    }

    @property
    def smp_import_map(self):
        smp_import_map = {
            'xml': {
                'imports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                    'import_choice': ('False,data/smp.xml', ('RDMO XML', _('File path')), 'xml'),
                    'import_choice_validators': {
                        'text': [FilePathExtensionValidator('.xml')]
                    },
                    'import_choice_attributes': {
                        'text': {
                            'placeholder': _('example_folder/example_file_name.xml'),
                        }
                    }
                },
                'process_method': self.process_xml,
                'process_method_kwargs': {}
            },
            'citation': {
                'imports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                    'import_choice': ('False,CITATION.cff', ('CITATION', _('File path')), 'citation'),
                    'import_choice_validators': {
                        'text': [FilePathExtensionValidator('.cff')]
                    },
                    'import_choice_attributes': {
                        'text': {
                            'placeholder': 'CITATION.cff',
                        }
                    }
                },
                'process_method': self.process_citation,
                'process_method_kwargs': {'get_citation': self.get_citation}
            },
            'codemeta': {
                'imports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                    'import_choice': ('False,codemeta.json', ('CodeMeta', _('File path')), 'codemeta'),
                    'import_choice_validators': {
                        'text': [FilePathExtensionValidator('.json')]
                    },
                    'import_choice_attributes': {
                        'text': {
                            'placeholder': 'codemeta.json',
                        }
                    }
                },
                'process_method': self.process_codemeta,
                'process_method_kwargs': {'get_codemeta': self.get_codemeta}
            },
            'license': {
                'imports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                    'import_choice': ('False', 'LICENSE', 'license'),
                    'import_choice_validators': {},
                    'import_choice_attributes': {}
                },
                'process_method': self.process_license,
                'process_method_kwargs': {'get_license': self.get_license}
            },
            'sbom': {
                'imports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                    'import_choice': ('False', _('Repository dependency graph'), 'sbom'),
                    'import_choice_validators': {},
                    'import_choice_attributes': {}
                },
                'process_method': self.process_sbom,
                'process_method_kwargs': {'get_sbom': self.get_sbom}
            },
            'languages': {
                'imports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                    'import_choice': ('False', _('Repository languages'), 'languages'),
                    'import_choice_validators': {},
                    'import_choice_attributes': {}
                },
                'process_method': self.process_languages,
                'process_method_kwargs': {'get_languages': self.get_languages}
            }
        }

        return smp_import_map

    @property
    def smp_import_choices(self):
        smp_import_choices = {}
        if self.current_project is None or self.current_project.catalog.uri_path == 'smp':
            smp_import_choices = {
                'choices': [
                    v.get('imports', {}).get('import_choice') for v in self.smp_import_map.values()
                ],
                'choice_validators': {
                    k:v.get('imports', {}).get('import_choice_validators') for k,v in self.smp_import_map.items()
                    if len(v.get('imports', {}).get('import_choice_validators', {})) > 0
                },
                'choice_attributes': {
                    k:v.get('imports', {}).get('import_choice_attributes') for k,v in self.smp_import_map.items()
                    if len(v.get('imports', {}).get('import_choice_attributes', {})) > 0
                }
            }

        return smp_import_choices

    def process_import(
        self, *, request, headers, request_urls, import_choice_warnings,
        default_project_title, import_success_template, import_success_context
    ):
        '''Process information from web services and update or create projects with this information. '''

        # 1. Create (or extract from repo xml file) Project() instance
        self.create_import_project(headers, request_urls.get('xml'), default_project_title)

        # 2. Create Value() instances for all import data found in repo (and repo xml file if exists)
        import_values = self.get_import_values(headers, request_urls)

        if len(import_values) == 0:
            return render(request, 'core/error.html', {
                'title': _('Import error'),
                'errors': [_("Either no information was found in the repository, or it could not be imported.")]
            }, status=200)

        # 3. Create xml file with all info from repo (and from xml file in repo if exists)
        xml_response = self.create_import_xml_file(request, import_values, request_urls)

        request.session['import_file_name'] = handle_fetched_file(xml_response.content)

        if import_choice_warnings is None:
            if self.current_project:
                return redirect('project_update_import', self.current_project.id)
            else:
                return redirect('project_create_import')

        return render(
            request,
            import_success_template,
            import_success_context,
            status=200
        )

    def merge_licenses(self, new_license_values, import_values):
        '''Merge license information from all imported sources to unique SMP license values.

        Example: import sources are the CITATION.cff file and the repository LICENSE.

        If the information in both sources is the same license, only one value is created.
        If the information in both sources differs, multiple but unique values are created.

        '''

        existing_license_option_uris = [
            v.option.uri for v in import_values
            if v.attribute.uri == self.metadata_attr_mapping.get('license')
        ]

        grouped_new_license_values = reduce(partial(groupby_values, groupby='option'), new_license_values, {})
        unique_new_license_values = [value_list[0] for value_list in grouped_new_license_values.values()]
        for v in unique_new_license_values:
            if v.option.uri not in existing_license_option_uris:
                import_values.append(v)

        return import_values

    def merge_languages(self, new_language_values, import_values):
        '''Merge language information from all imported sources to unique SMP language values.
        Furthermore, merged values are sorted by the index of matching existing project language values.

        Example 1: import sources are the RDMO xml file and the repository languages.

        If the information in both sources is the same language, only one value is created.
        If the information in both sources differs, multiple but unique values are created.

        Example 2: repository data import to an existing project in RDMO
        (i.e. project update instead of project creation).

        If these are the project and imported language values:
        - project language values = 0. Python, 1. JavaScript
        - merged imported language values = 0. Javascript, 1. HTML, 2. R

        Then merge_languages() will return: 1. JavaScript, 2. HTML, 3. R
        - The index for the imported "JavaScript" matches the corresponding index
          of the "Javascript" in the project (1 instead of 0).
        - The imported "HTML" and "R" are `appended`, i.e. they get new indizes that
          no project language value has (no imported value gets an index of 0).
        - If imported, the project language values will be: 0. Python, 1. JavaScript, 2. HTML, 3. R

        '''

        import_values_languages = [
            (v.collection_index, v.text) for v in import_values
            if v.attribute.uri == self.metadata_attr_mapping.get('language')
        ]

        project_languages = []
        if self.current_project:
            project_language_values = self.current_project.values.filter(
                attribute__uri=self.metadata_attr_mapping.get('language')
            ).order_by('collection_index')

            project_languages = [(v.collection_index, v.text) for v in project_language_values ]

        grouped_new_language_values = reduce(partial(groupby_values, groupby='text'), new_language_values, {})
        unique_new_language_values = [value_list[0] for value_list in grouped_new_language_values.values()]

        matching_languages = {} # imported languages that already exist in current_project
        for import_index, language_value in enumerate(unique_new_language_values):
            language = language_value.text
            matching_project_language_index, matching_project_language = next(
                ((i, lang) for (i, lang) in project_languages if lang.lower() == language.lower()),
                (None, None)
            )

            if matching_project_language:
                language_value.collection_index = matching_project_language_index
                matching_languages[import_index] = language_value

        new_values = []
        index_to_update = []
        for i, v in enumerate(unique_new_language_values):
            language = v.text.lower()
            if i in matching_languages:
                new_values.append(matching_languages.get(i))
                continue

            index = i + len(import_values_languages)
            if index in [j for (j, _lang) in project_languages]:
                index_to_update.append(v)
                continue

            if language not in [lang.lower() for (j, lang) in import_values_languages]:
                v.collection_index = index
                new_values.append(v)

        if len(index_to_update) > 0:
            usable_matching_language_indizes = [
                i for i in matching_languages
                if i not in [j for (j, o) in project_languages]
            ]
            new_values_language_indizes = [v.collection_index for v in new_values]

            # starting_index accounts for project languages, import_values languages and new_values languages
            max_project_language_index = (
                max([j for (j, _lang) in project_languages])
                if len(project_languages) > 0
                else 0
            )
            max_import_values_language_index = (
                max([j for (j, _lang) in import_values_languages])
                if len(import_values_languages) > 0
                else 0
            )
            max_new_values_language_index = (
                max(new_values_language_indizes)
                if len(new_values_language_indizes) > 0
                else 0
            )
            starting_index = 1 + max(
                max_project_language_index, max_import_values_language_index, max_new_values_language_index
            )

            available_indizes = [
                *usable_matching_language_indizes,
                *list(range(starting_index, (starting_index + len(index_to_update))))
            ]

            for i, v in enumerate(index_to_update):
                index = available_indizes[i]
                v.collection_index = index
                new_values.append(v)

        import_values.extend(new_values)

        return import_values

    def merge_dependencies(self, new_dependencies_values, import_values):
        '''Merge dependency information from all imported sources to a single string.

        If there is a dependecies value in the project, return a value that merges its text
        with the imported information. Otherwise, return a value with the imported information.

        Example: imported dependencies are "requests" and "PyYAML", and project dependency is "rdmo".

        merge_dependencies() returns a value with text: rdmo\nrequests\nPyYAML.

        '''

        existing_dependencies_value_list = [
            (i, v) for i, v in enumerate(import_values)
            if v.attribute.uri == self.metadata_attr_mapping.get('dependencies')
        ]

        # There is only one value for dependencies, so if there are multiple,
        # merge all their texts and append only one to import_values
        grouped_new_dependencies_values = reduce(partial(groupby_values, groupby='text'), new_dependencies_values, {})
        unique_new_dependencies_texts = [value_list[0].text for value_list in grouped_new_dependencies_values.values()]
        new_dependencies_text = '\n'.join(unique_new_dependencies_texts)

        # if no value for dependencies in import_values,
        # then append the first new value with all dependency texts (if many)
        if len(existing_dependencies_value_list) == 0 and len(new_dependencies_values) > 0:
            new_value = new_dependencies_values[0]
            new_value.text = new_dependencies_text
            import_values.append(new_value)
        elif len(existing_dependencies_value_list) > 0:
            dependencies_value_index, dependencies_value = existing_dependencies_value_list[0]
            new_value_text = (
                dependencies_value.text + new_dependencies_text
                if dependencies_value.text.endswith('\n')
                else f'{dependencies_value.text}\n{new_dependencies_text}'
            )
            dependencies_value.text = new_value_text

            # There is only one dependencies value per project, delete duplicates if they exist
            duplicated_dependencies_value_indices = [
                i for (i, v) in existing_dependencies_value_list
                if i != dependencies_value_index
            ]
            if len(duplicated_dependencies_value_indices) > 0:
                for i in duplicated_dependencies_value_indices:
                    import_values.pop(i)

        return import_values

    def merge_dependency_licenses(self, new_dependency_licenses_values, import_values):
        '''Merge dependency license information from all imported sources to a single string.

        If there is a dependecy licenses value in the project, return a value that merges its text
        with the imported information. Otherwise, return a value with the imported information.

        Example: imported dependency licenses are "MIT (package_1)" and "Apache 2.0 (package_2, package_3)",
        and project dependency license is "AGPL 3.0 (package_0)".

        merge_dependency_licenses() returns a value with text:
        "AGPL 3.0 (package_0)\nMIT (package_1)\nApache 2.0 (package_2, package_3)".

        '''

        existing_dependency_licenses_value_list = [
            (i, v) for i, v in enumerate(import_values)
            if v.attribute.uri == self.metadata_attr_mapping.get('dependency_licenses')
        ]

        # Only one value for dependency licenses, so if there are multiple,
        # merge all their texts and append only one to import_values
        grouped_new_dependency_licenses_values = reduce(
            partial(groupby_values, groupby='text'), new_dependency_licenses_values, {}
        )
        unique_new_dependency_licenses_texts = [
            value_list[0].text for value_list in grouped_new_dependency_licenses_values.values()
        ]
        new_dependency_licenses_text = '\n'.join(unique_new_dependency_licenses_texts)

        # if no value for dependency licenses in import_values,
        # then append the first new value with all dependency license texts (if many)
        if len(existing_dependency_licenses_value_list) == 0 and len(new_dependency_licenses_values) > 0:
            new_value = new_dependency_licenses_values[0]
            new_value.text = new_dependency_licenses_text
            import_values.append(new_value)
        elif len(existing_dependency_licenses_value_list) > 0:
            dependency_licenses_value_index, dependency_licenses_value = existing_dependency_licenses_value_list[0]
            new_value_text = (
                dependency_licenses_value.text + new_dependency_licenses_text
                if dependency_licenses_value.text.endswith('\n')
                else f'{dependency_licenses_value.text}\n{new_dependency_licenses_text}'
            )
            dependency_licenses_value.text = new_value_text

            # There is only one dependency licenses value per project, delete duplicates if they exist
            duplicated_dependency_licenses_value_indices = [
                i for (i, v) in existing_dependency_licenses_value_list
                if i != dependency_licenses_value_index
            ]
            if len(duplicated_dependency_licenses_value_indices) > 0:
                for i in duplicated_dependency_licenses_value_indices:
                    import_values.pop(i)

        return import_values

    def merge_title(self, new_title_values, import_values):
        '''Append title value from first import source (import sources are sorted by importance). '''

        existing_title_value_list = [
            v for v in import_values
            if v.attribute.uri == self.metadata_attr_mapping.get('title')
        ]

        if len(existing_title_value_list) == 0:
            import_values.append(new_title_values[0])

        return import_values

    def merge_contributors(self, new_contributor_values, import_values):
        '''Merge contributor information from all imported sources.
        Furthermore, merged values are sorted by the index of matching existing project contributor values.

        Example 1: import sources are the RDMO xml file and the CITATION.cff file.

        If the information in both sources is the same (by orcid), merged values per contributor are unique.
        If the information in both sources differs, multiple but unique values per contributor are created.

        Example 2: repository data import to an existing project in RDMO
        (i.e. project update instead of project creation).

        If these are the project and imported contributor values:
        - project values:
            0. {family-names: Musterfrau, given-names: Muriel, orcid: 123-456}
        - imported contributor values:
            0. {family-names: Schmidt, given-names: Peter, orcid: 789-012},
            1. {family-names: Musterfrau, given-names: Muriel P., orcid: 123-456}

        Then merge_contributors() will return:
            0. {family-names: Musterfrau, given-names: Muriel P., orcid: 123-456},
            1. {family-names: Schmidt, given-names: Peter, orcid: 789-012}
        Because:
        - The orcid for the imported "Muriel P. Musterfrau" matches the corresponding orcid of the "Muriel Musterfrau"
        in the project (imported values of "Muriel P. Musterfrau" get index 0 instead of 1).
        - The imported "Peter Schmidt" is `appended`, i.e. he gets index 1 which no project contributor value has.
        - If imported, the project contributor values will be:
            0. {family-names: Musterfrau, given-names: Muriel P., orcid: 123-456},
            1. {family-names: Schmidt, given-names: Peter, orcid: 789-012}

        '''

        import_values_contributor_indizes = [
            v.set_index for v in import_values
            if v.attribute.uri == self.metadata_attr_mapping.get('contributor', {}).get('id')
        ]
        import_values_orcids = [
            v.text for v in import_values
            if v.attribute.uri == self.metadata_attr_mapping.get('contributor', {}).get('orcid')
        ]

        project_contributor_indizes = []
        project_orcids = []
        if self.current_project:
            project_contributor_indizes = [
                v.set_index
                for v in self.current_project.values.filter(
                    attribute__uri=self.metadata_attr_mapping.get('contributor', {}).get('id')
                ).order_by('set_index')
            ]
            project_orcids = [
                (v.set_index, v.text)
                for v in self.current_project.values.filter(
                    attribute__uri=self.metadata_attr_mapping.get('contributor', {}).get('orcid')
                ).order_by('set_index')
            ]

        employment_attributes = [
            self.metadata_attr_mapping.get('contributor', {}).get(metadata)
            for metadata in ['role', 'affiliation', 'ror-id', 'ror-autocomplete']
        ]

        grouped_new_contributor_values = reduce(
            partial(groupby_values, groupby='set_index'),
            [v for v in new_contributor_values if v.attribute.uri not in employment_attributes],
            {}
        )
        grouped_new_contributor_values = reduce(
            partial(groupby_values, groupby='set_prefix'),
            [v for v in new_contributor_values if v.attribute.uri in employment_attributes],
            grouped_new_contributor_values
        )

        matching_contributors = {} # imported contributors that already exist in current_project
        for import_index, contributor_values_list in grouped_new_contributor_values.items():
            contributor_orcid = next(
                (v.text for v in contributor_values_list
                 if v.attribute.uri == self.metadata_attr_mapping.get('contributor', {}).get('orcid')),
                None
            )
            matching_project_contributor_index, matching_project_orcid = next(
                ((i, o) for (i, o) in project_orcids if contributor_orcid is not None and o == contributor_orcid),
                (None, None)
            )

            if matching_project_orcid:
                for v in contributor_values_list:
                    attr_uri = v.attribute.uri

                    if attr_uri not in employment_attributes:
                        v.set_index = matching_project_contributor_index

                    if attr_uri in employment_attributes:
                        v.set_prefix = str(matching_project_contributor_index) # set_prefix is a string field

                matching_contributors[int(import_index)] = contributor_values_list

        new_values = []
        index_to_update = []
        for i, (import_index, contributor_values_list) in enumerate(grouped_new_contributor_values.items()):
            contributor_orcid = next(
                (v.text for v in contributor_values_list
                 if v.attribute.uri == self.metadata_attr_mapping.get('contributor', {}).get('orcid')),
                None
            )
            if contributor_orcid in import_values_orcids:
                continue

            if int(import_index) in matching_contributors:
                new_values.extend(matching_contributors.get(int(import_index)))
                continue

            index = i + len(import_values_contributor_indizes)
            if index in project_contributor_indizes:
                index_to_update.append(contributor_values_list)
                continue

            for v in contributor_values_list:
                attr_uri = v.attribute.uri

                if attr_uri not in employment_attributes:
                    v.set_index = index

                if attr_uri in employment_attributes:
                    v.set_prefix = str(index) # set_prefix is a string field

                new_values.append(v)

        if len(index_to_update) > 0:
            remaining_matching_contributor_indizes = [
                i for i in matching_contributors
                if i not in project_contributor_indizes
            ]
            new_values_contributor_indizes = [
                v.set_index for v in new_values
                if v.attribute.uri == self.metadata_attr_mapping.get('contributor', {}).get('id')
            ]

            # starting_index accounts for project contributors, import_values contributors and new_values contributors
            max_project_contributor_index = (
                max(project_contributor_indizes)
                if len(project_contributor_indizes) > 0
                else 0
            )
            max_import_values_contributor_index = (
                max(import_values_contributor_indizes)
                if len(import_values_contributor_indizes) > 0
                else 0
            )
            max_new_values_contributor_index = (
                max(new_values_contributor_indizes)
                if len(new_values_contributor_indizes) > 0
                else 0
            )
            starting_index = 1 + max(
                max_project_contributor_index,
                max_import_values_contributor_index,
                max_new_values_contributor_index
            )

            available_indizes = [
                *remaining_matching_contributor_indizes,
                *list(range(starting_index, (starting_index + len(index_to_update))))
            ]
            available_indizes = list(set(available_indizes))

            for i, contributor_values_list in enumerate(index_to_update):
                index = available_indizes[i]
                for v in contributor_values_list:
                    attr_uri = v.attribute.uri

                    if attr_uri not in employment_attributes:
                        v.set_index = index

                    if attr_uri in employment_attributes:
                        v.set_prefix = str(index) # set_prefix is a string value

                    new_values.append(v)

        import_values.extend(new_values)
        merged_new_contributors = len(new_values) > 0

        return import_values, merged_new_contributors

    def merge_pids(self, new_pid_values, import_values):
        '''Merge pid information from all imported sources to unique SMP pid values.

        Example: import sources are the CITATION.cff file and the RDMO xml file.

        If the information in both sources is the same pid (by type), only one value is created.
        If the information in both sources differs, multiple but unique values are created.

        '''

        existing_pid_option_uris = [
            v.option.uri for v in import_values
            if v.attribute.uri == self.metadata_attr_mapping.get('pid')
        ]

        grouped_new_pid_values = reduce(partial(groupby_values, groupby='option'), new_pid_values, {})
        unique_new_pid_values = [value_list[0] for value_list in grouped_new_pid_values.values()]

        new_values = [
            v for v in unique_new_pid_values
            if v.option.uri not in existing_pid_option_uris
        ]

        import_values.extend(new_values)
        merged_new_pids = len(new_values) > 0

        return import_values, merged_new_pids

    def merge_application_class(self, new_application_class_values, import_values):
        '''Append application class value with highest class. '''

        existing_application_class_value_list = [
            (i, v) for i, v in enumerate(import_values)
            if v.attribute.uri == 'https://rdmorganiser.github.io/terms/domain/smp/application-class'
        ]

        application_class_values = [
            v for v in [*new_application_class_values, *import_values]
            if v.attribute.uri == 'https://rdmorganiser.github.io/terms/domain/smp/application-class'
        ]
        highest_class_option = max([int(v.option.uri.split('/')[-1]) for v in application_class_values])

        application_class_v = next(
            v for v in application_class_values
            if int(v.option.uri.split('/')[-1]) == highest_class_option
        )

        if len(existing_application_class_value_list) == 0:
            import_values.append(application_class_v)
        else:
            application_class_value_index, application_class_value = existing_application_class_value_list[0]
            application_class_value.option = application_class_v.option

            duplicated_application_class_value_indices = [
                i for (i, v) in existing_application_class_value_list
                if i != application_class_value_index
            ]
            if len(duplicated_application_class_value_indices) > 0:
                for i in duplicated_application_class_value_indices:
                    import_values.pop(i)

        return import_values

    def check_attribute(self, attr_uri):
        '''Check if attribute exists and is still used by project catalog. '''

        v_attribute = self.get_attribute(attr_uri)

        # Keep only values with a corresponding question, question set or page (attribute)
        # in self.import_project.catalog (which equals current_project.catalog)
        catalog_questions = self.get_questions(self.import_project.catalog)
        catalog_questionsets = get_questionsets(self.import_project.catalog)
        catalog_pages = get_pages(self.import_project.catalog)
        if (
                v_attribute and (
                    catalog_questions.get(attr_uri) or
                    catalog_questionsets.get(attr_uri) or
                    catalog_pages.get(attr_uri)
                )
            ):
            return v_attribute

    def create_value(
        self, attribute, *, set_collection=False, set_prefix='', set_index=0,
        collection_index=0, text=None, option=None, external_id=None
    ):
        value = Value()
        value.attribute = attribute
        value.set_prefix = set_prefix
        value.set_index = set_index
        value.set_collection = set_collection
        value.collection_index = collection_index

        if text:
            value.text = text
        if option:
            value.option = option
        if external_id:
            value.external_id = external_id

        return value

    def get_license_option(self, license_optionset_uri, license_id):
        options = get_optionset_options(license_optionset_uri)

        collection_index, option = next(
            ((i, o) for i, o in enumerate(options) if o.text == license_id),
            (None, None)
        )

        if option is None:
            collection_index, option = next(
                (i, o) for i, o in enumerate(options)
                if o.uri == 'https://rdmorganiser.github.io/terms/options/software-license/other-license'
            )

        return collection_index, option

    def get_license_value(self, _id):
        collection_index, license_option = self.get_license_option(
            license_optionset_uri='https://rdmorganiser.github.io/terms/options/software-license',
            license_id=_id
        )
        v_attribute = self.check_attribute(self.metadata_attr_mapping.get('license'))

        value = None
        if v_attribute:
            license_text = (
                _id if license_option.uri == 'https://rdmorganiser.github.io/terms/options/software-license/other-license'
                else ''
            )
            value = self.create_value(
                v_attribute,
                collection_index=collection_index,
                text=license_text,
                option=license_option
            )

        return value

    def get_cff_licenses(self, cff_data):
        cff_licenses = cff_data.get('license')

        license_values = []
        if cff_licenses is None:
            return license_values

        if isinstance(cff_licenses, str):
            cff_licenses = [cff_licenses]

        for _id in cff_licenses:
            license_value = self.get_license_value(_id)
            if license_value:
                license_values.append(license_value)

        return license_values

    def get_cff_authors(self, cff_data):
        contributor_values = []

        for i, author in enumerate(cff_data.get('authors', [])):
            type = (
                'person'
                if (author.get('given-names') or author.get('family-names'))
                else 'entity'
            )

            set_v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get('id'))
            if set_v_attribute is None:
                continue

            # SET VALUE
            set_label = (
                f'{author.get("given-names", "")} {author.get("family-names", "")}'.strip()
                if type == 'person'
                else author.get('name')
            )
            set_label = set_label if (set_label and set_label != '') else f'cff author # {i+1}'
            contributor_values.append(self.create_value(
                set_v_attribute,
                set_collection=True,
                set_index=i,
                text=set_label
            ))

            # TYPE VALUE
            type_v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get('type'))
            option_uri = (
                    'https://rdmo.mpdl.mpg.de/terms/options/partner-types/person'
                    if type == 'person'
                    else 'https://rdmo.mpdl.mpg.de/terms/options/partner-types/entity'
                )
            type_v_option = self.get_option(option_uri)
            if type_v_attribute and type_v_option:
                contributor_values.append(self.create_value(
                    type_v_attribute,
                    set_collection=True,
                    set_index=i,
                    option=type_v_option
                ))

            for k, v in author.items():
                if v is None:
                    continue

                # no SMP field for name or website for a contributor of type person,
                # or orcid for a contributor of type entity
                # but possible by cff schema
                if (
                    ((k == 'name' or k == 'website') and type == 'person') or
                    (k == 'orcid' and type == 'entity')
                ):
                    continue

                v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get(k))
                if k != 'affiliation' and v_attribute:
                    contributor_values.append(self.create_value(
                        v_attribute,
                        set_collection=True,
                        set_index=i,
                        text=v
                    ))

                elif k == 'affiliation' and v_attribute:
                    cff_a_str = v
                    affiliations = cff_a_str.split(' & ')
                    for j, a in enumerate(affiliations):
                        contributor_values.append(self.create_value(
                            v_attribute,
                            set_collection=True,
                            set_prefix=str(i), # set_prefix is a string field
                            set_index=j,
                            text=a
                        ))

        return contributor_values

    def get_pid_option(self, pid_optionset_uri, identifier_type):
        options = get_optionset_options(pid_optionset_uri)

        collection_index, option = next(
            ((i, o) for i, o in enumerate(options) if identifier_type and o.uri.endswith(identifier_type)),
            (None, None)
        )

        if option is None:
            collection_index, option = next(
                (i, o) for i, o in enumerate(options)
                if o.uri == 'https://rdmorganiser.github.io/terms/options/software_identifier/other'
            )

        return collection_index, option

    def get_cff_identifiers(self, cff_data):
        _identifiers = []
        _identifier_types = []

        _identifiers.extend(cff_data.get('identifiers', []))
        _identifier_types.extend([i.get('type') for i in cff_data.get('identifiers', [])])

        if 'doi' in cff_data and 'doi' not in _identifier_types:
            _identifiers.append({'type': 'doi', 'value': cff_data.get('doi')})

        if 'url' in cff_data and 'url' not in _identifier_types:
            _identifiers.append({'type': 'url', 'value': cff_data.get('url')})

        pid_values = []
        for identifier in _identifiers:
            value = identifier.get('value')
            if value is None or value == '':
                continue

            identifier_type = identifier.get('type')
            collection_index, identifier_option = self.get_pid_option(
                'https://rdmorganiser.github.io/terms/options/software_identifier',
                identifier_type
            )
            v_attribute = self.check_attribute(self.metadata_attr_mapping.get('pid'))
            if identifier_option and v_attribute:
                pid_values.append(self.create_value(
                    v_attribute,
                    collection_index=collection_index,
                    text=value,
                    option=identifier_option
                ))

        return pid_values

    def get_title(self, metadata_dict, key):
        dict_value = metadata_dict.get(key)
        v_attribute = self.check_attribute(self.metadata_attr_mapping.get('title'))

        title_value = None
        if dict_value and v_attribute:
            title_value = self.create_value(v_attribute, text=dict_value)

        return title_value

    def get_codemeta_licenses(self, codemeta_data):
        codemeta_licenses = codemeta_data.get('license')

        license_values = []
        if codemeta_licenses is None:
            return license_values

        if isinstance(codemeta_licenses, str):
            codemeta_licenses = [codemeta_licenses]

        for spdx_url in codemeta_licenses:
            _id = spdx_url.removeprefix('https://spdx.org/licenses/')
            license_value = self.get_license_value(_id)
            if license_value:
                license_values.append(license_value)

        return license_values

    def get_codemeta_authors(self, codemeta_data):
        raw_codemeta_authors = []
        for key in ['author', 'contributor', 'maintainer']:
            if key in codemeta_data:
                raw_author = codemeta_data.get(key)
                if isinstance(raw_author, list):
                    raw_codemeta_authors.extend(raw_author)
                elif isinstance(raw_author, dict):
                    raw_codemeta_authors.append(raw_author)

        codemeta_authors = []
        codemeta_roles = []
        for author in raw_codemeta_authors:
            raw_type = (
                author.get('@type') if '@type' in author
                else(author.get('type') if 'type' in author else None)
            )

            type = (
                'person' if raw_type == 'Person'
                else('entity' if raw_type == 'Organization' else raw_type)
            )

            if type == 'Role':
                codemeta_roles.append(author)

            if type != 'person' and type != 'entity':
                continue

            author['type'] = type
            codemeta_authors.append(author)

        contributor_values = []
        for i, author in enumerate(codemeta_authors):
            type = author.pop('type')

            set_v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get('id'))
            if set_v_attribute is None:
                continue

            # SET VALUE
            set_label = (
                f'{author.get("givenName", "")} {author.get("familyName", "")}'.strip()
                if type == 'person'
                else author.get('name')
            )
            set_label = set_label if (set_label and set_label != '') else f'cff author # {i+1}'
            contributor_values.append(self.create_value(
                set_v_attribute,
                set_collection=True,
                set_index=i,
                text=set_label
            ))

            # TYPE VALUE
            type_v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get('type'))
            option_uri = (
                    'https://rdmo.mpdl.mpg.de/terms/options/partner-types/person'
                    if type == 'person'
                    else 'https://rdmo.mpdl.mpg.de/terms/options/partner-types/entity'
                )
            type_v_option = self.get_option(option_uri)
            if type_v_attribute and type_v_option:
                contributor_values.append(self.create_value(
                    type_v_attribute,
                    set_collection=True,
                    set_index=i,
                    option=type_v_option
                ))

            for k, v in author.items():
                if v is None or v == '':
                    continue

                # no SMP field for name for a contributor of type person
                if (k == 'name' and type == 'person'):
                    continue

                v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get(k))
                if k in ['givenName', 'familyName', 'name'] and v_attribute:
                    contributor_values.append(self.create_value(
                        v_attribute,
                        set_collection=True,
                        set_index=i,
                        text=v
                    ))

                v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get('orcid'))
                if (k == 'id' or k == '@id') and author.get(k).startswith('https://orcid.org/') and v_attribute:
                    contributor_values.append(self.create_value(
                        v_attribute,
                        set_collection=True,
                        set_index=i,
                        text=author.get(k)
                    ))

                if k == 'affiliation':
                    affiliations = []
                    if isinstance(v, list):
                        affiliations.extend(v)
                    elif isinstance(v, dict):
                        affiliations.append(v)

                    for j, a in enumerate(affiliations):
                        affiliation_name = a.get('name')
                        affiliation_id = (
                            a.get('id') if 'id' in a
                            else (a.get('@id') if '@id' in a else None)
                        )

                        v_attribute = self.check_attribute(
                            self.metadata_attr_mapping.get('contributor', {}).get('affiliation')
                        )
                        if affiliation_name and v_attribute:
                            contributor_values.append(self.create_value(
                                v_attribute,
                                set_collection=True,
                                set_prefix=str(i), # set_prefix is a string field
                                set_index=j,
                                text=affiliation_name
                            ))

                        v_attribute = self.check_attribute(
                            self.metadata_attr_mapping.get('contributor', {}).get('ror-id')
                        )
                        if affiliation_id and affiliation_id.startswith('https://ror.org/') and v_attribute:
                            contributor_values.append(self.create_value(
                                v_attribute,
                                set_collection=True,
                                set_prefix=str(i), # set_prefix is a string field
                                set_index=j,
                                text=affiliation_id
                            ))


        for i, role in enumerate(codemeta_roles):
            author_id = (
                role.get('author') if 'author' in role
                else (
                    role.get('contributor') if 'contributor' in role
                    else (role.get('maintainer') if 'maintainer' in role else None)
                )
            )

            if author_id:
                author_index = next(
                    (
                        v.set_index for v in contributor_values
                        if (
                            v.attribute.uri == self.metadata_attr_mapping.get('contributor', {}).get('orcid') and
                            v.text == author_id
                        )
                    ),
                    None
                )

                role_name = role.get('roleName')
                if author_index and role_name:
                    author_affiliation_indizes = [
                        a.set_index for a in [v for v in contributor_values if v.set_prefix == str(author_index)]
                    ]
                    role_index = (
                        i + 1 + max(author_affiliation_indizes)
                        if len(author_affiliation_indizes) > 0
                        else i
                    )
                    v_attribute = self.check_attribute(self.metadata_attr_mapping.get('contributor', {}).get('role'))
                    contributor_values.append(self.create_value(
                        v_attribute,
                        set_collection=True,
                        set_prefix=str(author_index), # set_prefix is a string field
                        set_index=role_index,
                        text=role_name
                    ))

        return contributor_values

    def get_codemeta_identifiers(self, codemeta_data):
        identifiers = []
        codemeta_identifiers = codemeta_data.get('identifier')
        if isinstance(codemeta_identifiers, list):
            identifiers.extend(codemeta_identifiers)
        elif isinstance(codemeta_identifiers, dict):
            identifiers.append(codemeta_identifiers)

        pid_values = []
        for identifier in identifiers:
            value = identifier.get('value')
            if value is None or value == '':
                continue

            identifier_type = (
                identifier.get('propertyID') if 'propertyID' in identifier
                else (identifier.get('name') if 'name' in identifier else None)
            )
            if identifier_type:
                identifier_type = (
                    'swh' if identifier_type.lower()  == 'software heritage identifier'
                    else identifier_type.lower()
                )
                collection_index, identifier_option = self.get_pid_option(
                    'https://rdmorganiser.github.io/terms/options/software_identifier',
                    identifier_type
                )
                v_attribute = self.check_attribute(self.metadata_attr_mapping.get('pid'))
                if identifier_option and v_attribute:
                    pid_values.append(self.create_value(
                        v_attribute,
                        collection_index=collection_index,
                        text=value,
                        option=identifier_option
                    ))

        return pid_values

    def process_xml(self, url, import_values, headers):
        metadata_merge_method_mapping = {
            'license': self.merge_licenses,
            'language': self.merge_languages,
            'dependencies': self.merge_dependencies,
            'dependency_licenses': self.merge_dependency_licenses,
            'title': self.merge_title,
            'contributor': self.merge_contributors,
            'pid': self.merge_pids
        }

        if self.xml_import_plugin is None:
            return import_values

        # if xml values have attributes that do not exist in catalog anymore v.attribute == None
        valid_values = [v for v in self.xml_import_plugin.values if v.attribute]
        self.xml_import_plugin.values = valid_values

        contributor_attribute_uris = self.metadata_attr_mapping.get('contributor', {}).values()

        grouped_import_values = reduce(
            partial(groupby_values, groupby='attribute'),
            [v for v in import_values if v.attribute.uri not in contributor_attribute_uris],
            {}
        )
        grouped_import_values['contributor'] = [
            v for v in import_values
            if v.attribute.uri in contributor_attribute_uris
        ]

        grouped_xml_values = reduce(
            partial(groupby_values, groupby='attribute'),
            [v for v in self.xml_import_plugin.values if v.attribute.uri not in contributor_attribute_uris],
            {}
        )
        grouped_xml_values['contributor'] = [
            v for v in self.xml_import_plugin.values
            if v.attribute.uri in contributor_attribute_uris
        ]

        for uri, xml_values_list in grouped_xml_values.items():
            if (
                uri not in grouped_import_values and
                # imported xml contributors and languages must always be merged:
                # they may have different order than matching project values
                uri != 'contributor' and
                uri != self.metadata_attr_mapping.get('language')
            ):
                import_values.extend(xml_values_list)
            else:
                metadata = next(
                    (metadata for metadata, attr in self.metadata_attr_mapping.items()
                     if isinstance(attr, str) and uri == attr),
                    None
                )
                metadata = metadata if metadata else (uri if uri == 'contributor' else None)
                if metadata:
                    merge_method = metadata_merge_method_mapping.get(metadata)
                    merged_result = merge_method(xml_values_list, import_values)
                    if isinstance(merged_result, tuple):
                        import_values = merged_result[0]
                    else:
                        import_values = merged_result

        return import_values

    def process_citation(self, url, import_values, headers, get_citation):
        # https://github.com/citation-file-format/citation-file-format/blob/main/schema-guide.md

        citation_content = get_citation(url, headers)
        cff_data = yaml.safe_load(citation_content) if citation_content else {}

        if 'title' in cff_data:
            title_value = self.get_title(cff_data, 'title')
            if title_value:
                import_values = self.merge_title([title_value], import_values)

        if 'license' in cff_data:
            license_values = self.get_cff_licenses(cff_data)
            if len(license_values) > 0:
                import_values = self.merge_licenses(license_values, import_values)

        found_new_contributors = False
        if 'authors' in cff_data:
            contributor_values = self.get_cff_authors(cff_data)
            if len(contributor_values) > 0:
                import_values, found_new_contributors = self.merge_contributors(contributor_values, import_values)

        found_new_pids = False
        if 'identifiers' in cff_data or 'doi' in cff_data or 'url' in cff_data:
            pid_values = self.get_cff_identifiers(cff_data)
            if len(pid_values) > 0:
                import_values, found_new_pids = self.merge_pids(pid_values, import_values)

        application_class_v_attribute = self.check_attribute('https://rdmorganiser.github.io/terms/domain/smp/application-class')
        application_class_option_uri = (
                'https://rdmorganiser.github.io/terms/options/application-class/2'
                if found_new_contributors
                else 'https://rdmorganiser.github.io/terms/options/application-class/1'
            )
        application_class_option = self.get_option(application_class_option_uri)

        if (
            (found_new_contributors or found_new_pids) and
            application_class_v_attribute and
            application_class_option
        ):
            application_class_value = self.create_value(
                application_class_v_attribute,
                option = application_class_option
            )
            import_values = self.merge_application_class([application_class_value], import_values)

        return import_values

    def process_codemeta(self, url, import_values, headers, get_codemeta):
        # https://github.com/citation-file-format/citation-file-format/blob/main/schema-guide.md

        codemeta_content = get_codemeta(url, headers)
        codemeta_data = json.loads(codemeta_content)


        if 'name' in codemeta_data:
            title_value = self.get_title(codemeta_data, 'name')
            if title_value:
                import_values = self.merge_title([title_value], import_values)

        if 'license' in codemeta_data:
            license_values = self.get_codemeta_licenses(codemeta_data)
            if len(license_values) > 0:
                import_values = self.merge_licenses(license_values, import_values)

        found_new_contributors = False
        if 'author' in codemeta_data or 'contributor' in codemeta_data or 'maintainer' in codemeta_data:
            contributor_values = self.get_codemeta_authors(codemeta_data)
            if len(contributor_values) > 0:
                import_values, found_new_contributors = self.merge_contributors(contributor_values, import_values)

        found_new_pids = False
        if 'identifier' in codemeta_data:
            pid_values = self.get_codemeta_identifiers(codemeta_data)
            if len(pid_values) > 0:
                import_values, found_new_pids = self.merge_pids(pid_values, import_values)

        application_class_v_attribute = self.check_attribute('https://rdmorganiser.github.io/terms/domain/smp/application-class')
        application_class_option_uri = (
                'https://rdmorganiser.github.io/terms/options/application-class/2'
                if found_new_contributors
                else 'https://rdmorganiser.github.io/terms/options/application-class/1'
            )
        application_class_option = self.get_option(application_class_option_uri)

        if (
            (found_new_contributors or found_new_pids) and
            application_class_v_attribute and
            application_class_option
        ):
            application_class_value = self.create_value(
                application_class_v_attribute,
                option = application_class_option
            )
            import_values = self.merge_application_class([application_class_value], import_values)

        return import_values

    def process_license(self, url, import_values, headers, get_license):
        _id = get_license(url, headers)

        if _id:
            value = self.get_license_value(_id)
            if value:
                import_values = self.merge_licenses([value], import_values)

        return import_values

    def process_sbom(self, url, import_values, headers, get_sbom):
        sbom = get_sbom(url, headers)
        dependencies, dependency_licenses = sbom.values()

        dependencies_attribute = self.check_attribute(self.metadata_attr_mapping.get('dependencies'))
        if dependencies and dependencies_attribute:
            dependencies_value = self.create_value(
                dependencies_attribute,
                text=dependencies
            )
            import_values = self.merge_dependencies([dependencies_value], import_values)

        dependency_licenses_attribute = self.check_attribute(self.metadata_attr_mapping.get('dependency_licenses'))
        if dependency_licenses and dependency_licenses_attribute:
            dependency_licenses_value = self.create_value(
                dependency_licenses_attribute,
                text=dependency_licenses
            )
            import_values = self.merge_dependency_licenses([dependency_licenses_value], import_values)

        application_class_v_attribute = self.check_attribute('https://rdmorganiser.github.io/terms/domain/smp/application-class')
        application_class_option_uri = (
            'https://rdmorganiser.github.io/terms/options/application-class/2'
            if dependency_licenses
            else 'https://rdmorganiser.github.io/terms/options/application-class/1'
        )
        application_class_option = self.get_option(application_class_option_uri)
        if (
            (dependencies or dependency_licenses) and
            application_class_v_attribute and
            application_class_option
        ):
            application_class_value = self.create_value(
                application_class_v_attribute,
                option = application_class_option
            )
            import_values = self.merge_application_class([application_class_value], import_values)


        return import_values

    def process_languages(self, url, import_values, headers, get_languages):
        languages = get_languages(url, headers)

        language_values = []
        v_attribute = self.check_attribute(self.metadata_attr_mapping.get('language'))
        if v_attribute and len(languages) > 0:
            for language in languages:
                language_values.append(self.create_value(
                    v_attribute,
                    text=language
                ))

            import_values = self.merge_languages(language_values, import_values)

        return import_values

    def get_import_values(self, headers, request_urls):
        '''Return a list with Value() instances to create an xml with all the info from the selected repository. '''

        import_values = []
        for import_option_key, import_option_url in request_urls.items():
            _imports, process_method, process_method_kwargs = self.smp_import_map.get(import_option_key).values()

            import_values = process_method(import_option_url, import_values, headers, **process_method_kwargs)

        def sort_by_external_id(e):
            # values without an external id come first
            # external id marks values used by option providers
            return e.external_id

        import_values.sort(key = sort_by_external_id)

        return import_values

    def get_citation(self, url, headers):
        raise NotImplementedError

    def get_license(self, url, headers):
        raise NotImplementedError

    def get_sbom(self, url, headers):
        raise NotImplementedError

    def get_languages(self, url, headers):
        raise NotImplementedError

    def create_import_project(self, headers, xml_url, default_title):
        '''Return a Project() instance that will be the basis to create an xml
        with all the info from the selected repository.

        If the user fills out the path to an RDMO xml file (optional), the Project() instance will have its
        information. If no file path is filled out, the Project() instance will be created from scratch.
        '''

        catalog = (
            self.current_project.catalog if self.current_project
            else Catalog.objects.get(uri='https://rdmorganiser.github.io/terms/questions/smp')
        )
        import_project = Project(
            catalog=catalog,
            title=default_title
        )
        xml_import_plugin = None

        if xml_url:
            xml_response = requests.get(xml_url, headers=headers)

            try:
                xml_response.raise_for_status()
                xml_content = handle_fetched_file(base64.b64decode(xml_response.json().get('content')))
                xml_import_plugin = self.get_import_plugin('xml', self.current_project)
                xml_import_plugin.file_name = xml_content

                if xml_import_plugin.check():
                    try:
                        # extract all Value() instances found in xml file
                        xml_import_plugin.process()
                        import_project = (
                            xml_import_plugin.project
                            if xml_import_plugin.project
                            else Project( # new Project() because xml_import_plugin.project is None
                                # xml_import_plugin.catalog == self.current_project.catalog
                                catalog=xml_import_plugin.catalog,
                                title='bla' # does not matter since updating existing project
                            )
                        )
                    except ValidationError:
                        pass

            except requests.HTTPError:
                pass

        self.import_project = import_project
        self.xml_import_plugin = xml_import_plugin

    def create_import_xml_file(self, request, import_values, request_urls):
        '''Return the xml_reponse of the temp_project created with the imported information from the repository.

        This xml_response will be processed and passed to either project_update_import or project_create_import,
        which are RDMO import views to either update or create projects from xml imports.

        '''

        # If Value() for title (title_value) exists and title_value != self.import_project.title,
        # update self.import_project.title if first import source was NOT xml
        title = next(
            (v.text for v in import_values
             if v.attribute.uri == self.metadata_attr_mapping.get('title')),
            None
        )
        first_import_source = next(iter(request_urls.keys()))
        if title and title != self.import_project.title and first_import_source != 'xml':
            self.import_project.title = title

        checked = [
            f'{v.attribute.uri}[{v.set_prefix}][{v.set_index}][{v.collection_index}]'
            for v in import_values
        ]

        snapshots = self.xml_import_plugin.snapshots if self.xml_import_plugin else []
        self.update_values(None, self.import_project.catalog, import_values, snapshots)

        self.import_project.site = get_current_site(request)
        self.import_project.save()

        tasks = self.xml_import_plugin.tasks if self.xml_import_plugin else []
        views = self.xml_import_plugin.views if self.xml_import_plugin else []
        save_import_values(self.import_project, import_values, checked)
        save_import_snapshot_values(self.import_project, snapshots, checked)
        save_import_tasks(self.import_project, tasks)
        save_import_views(self.import_project, views)

        xml_export_plugin = get_plugin('PROJECT_EXPORTS', 'xml')
        xml_export_plugin.project = self.import_project
        xml_response = xml_export_plugin.render()

        Project.objects.filter(pk=self.import_project.id).delete()

        return xml_response

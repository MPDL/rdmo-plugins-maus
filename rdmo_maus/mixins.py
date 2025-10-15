from .utils import get_project_license_ids, render_from_view, render_to_license

class SMPExportMixin:
    smp_exports_map = {
        'readme': {
            'form_choice_label': 'README',
            'form_choice_file_path': 'README.md',
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-readme',
                'title': 'README.md',
                'export_format': 'markdown',
                'language_code': 'en'
            }
        },
        'citation': {
            'form_choice_label': 'CITATION',
            'form_choice_file_path': 'CITATION.cff',
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-citation',
                'title': 'CITATION.cff',
                'export_format': 'plain'
            }
        },
        'licenses': {
            'form_choice_label': 'LICENSE',
            'form_choice_file_path': 'LICENSE',
            'render_function': render_to_license,
            'render_function_kwargs': {}
        },
        'report': {
            'form_choice_label': 'SMP Report',
            'form_choice_file_path': 'data/smp_report.html',
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-report',
                'title': 'smp_report.html',
                'export_format': 'html',
                'language_code': 'en'
            }
        }
    }

    @property
    def smp_exports(self):
        '''SMP-specific export choices if project has SMP Catalog.

        Returns a dictionary with export choices and their label and file path:
            smp_exports = {
                [export_choice_1]: {
                    'label': str,
                    'file_path': str
                },
                ...
            }

        '''

        smp_exports = {}
        if self.project.catalog.uri_path == 'smp':
            for k, v in self.smp_exports_map.items():
                if k == 'licenses':
                    license_ids = get_project_license_ids(self.project, self.snapshot)
                    license_count = len(license_ids)
                    if license_count == 1:
                        k = f'license_{license_ids[0].lower().replace("-", "_")}'
                    elif license_count > 1:
                        license_exports = {
                            f'license_{l.lower().replace("-", "_")}': {
                                'label': f'LICENSE_{l.replace("-", "_")}', 
                                'file_path': f'LICENSE_{l.replace("-", "_")}'
                            }
                            for l in license_ids
                        }
                        smp_exports.update(license_exports)
                        continue
                    else:
                        continue

                smp_exports[k] = {'label': v['form_choice_label'], 'file_path': v['form_choice_file_path']}

        return smp_exports

    def render_smp_export(self, choice):
        '''Render smp-specific export choice from self.smp_exports_map. 
        
        SMP projects may have multiple licenses: 
        - If only one license is defined, it will be exported as a LICENSE file with choice = 'licenses'.
        - For projects with multiple licenses:
            - To export all project licenses in a zip file use choice = 'licenses',
            - To export only one license, use choice = `license_{*license_name}`, 
              where *license_name must be a lowercased spdx license name with its hyphens resplaced with underscores. 
              Example: choice = 'license_lgpl_3.0_only' for LGPL-3.0-only
        '''
        
        if choice.startswith('license_'):
            form_choice_label, form_choice_file_path, render_function, kwargs = self.smp_exports_map['licenses'].values()
            kwargs['choice'] = choice.replace('license_', '')
        else:
            form_choice_label, form_choice_file_path, render_function, kwargs = self.smp_exports_map[choice].values()
        
        response = render_function(self.request, self.project, self.snapshot, **kwargs)
        return response
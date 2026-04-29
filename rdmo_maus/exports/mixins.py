from django.utils.translation import gettext_lazy as _

from ..forms.validators import validate_file_path, FilePathExtensionValidator
from ..utils import get_project_license_ids, render_from_view, render_to_license

class SMPExportMixin:
    '''A mixin class that provides export choices for projects with a Software Management Plan (SMP) catalogue.

    #####################
    ## SMP_EXPORTS_MAP ##
    #####################
    
    smp_exports_map (dict[str, dict[str, Any]]) contains a key value pair for every export choice and its values 
    are dictionaries with three keys ('exports', 'render_function' and 'render_function_kwargs'):

    # 'exports'
    'exports' assumes the use of ..forms.fields.py's MultivalueCheckboxMultipleChoiceField 
    for displaying the choices to the user.

    # 'render_function'
    'render_function' is the function that renders the export choice.

    # 'render_function_kwargs'
    'render_function_kwargs' contains the arguments expected by 'render_function'.
   
    Most render functions in this mixin expect a 'view_uri' argument. This is the URI of a view that the function uses
    as a template for creating the export choice. The views used by this mixin are:
    - "view-smp-citation.xml"
    - "view-smp-readme.xml"
    - "view-smp-report.xml" 
    and can be found [here](https://github.com/MPDL/rdmo-catalog/tree/MPG-catalogues/rdmorganiser/views).

    If an alternative template is required for any render_function, this view should be imported to RDMO
    and its URI should be specified as the 'view_uri' value.
    '''
    smp_exports_map = {
        'readme': {
            'exports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                'export_choice': ('False,README.md', ('README', _('File path')), 'readme'),
                'export_choice_validators': {
                    'text': [validate_file_path, FilePathExtensionValidator('.md')]
                },
                'export_choice_attributes': {
                    'text': {
                            'placeholder': 'README.md',
                        }
                }
            },
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-readme',
                'title': 'README.md',
                'export_format': 'markdown',
                'language_code': 'en'
            }
        },
        'citation': {
            'exports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                'export_choice': ('False,CITATION.cff', ('CITATION', _('File path')), 'citation'),
                'export_choice_validators': {
                    'text': [validate_file_path, FilePathExtensionValidator('.cff')]
                },
                'export_choice_attributes': {
                    'text': {
                            'placeholder': 'CITATION.cff',
                        }
                }
            },
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-citation',
                'title': 'CITATION.cff',
                'export_format': 'plain',
                'language_code': 'en'
            }
        },
        'licenses': {
            'exports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                'export_choice': (),
                'export_choice_validators': {
                    'text': [validate_file_path]    
                },
                'export_choice_attributes': {
                    'text': {
                            'placeholder': 'LICENSE',
                        }
                }
            },
            'render_function': render_to_license,
            'render_function_kwargs': {}
        },
        'report': {
            'exports': { # check MultivalueCheckboxMultipleChoiceField in ..forms.fields.py for details
                'export_choice': ('False,data/smp_report.html', (_('SMP Report'), _('File path')), 'report'),
                'export_choice_validators': {
                    'text': [validate_file_path, FilePathExtensionValidator('.html')]
                },
                'export_choice_attributes': {
                    'text': {
                            'placeholder': 'data/smp_report.html',
                        }
                }
            },
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
    def smp_export_choices(self):
        smp_export_choices = {}
        smp_export_choice_keys = []
        if self.project.catalog.uri_path == 'smp':
            smp_export_choices = {
                'choices': [
                    v.get('exports', {}).get('export_choice') for k,v in self.smp_exports_map.items() if k != 'licenses'
                ],
                'choice_validators': {
                    k:v.get('exports', {}).get('export_choice_validators') for k,v in self.smp_exports_map.items()
                    if (len(v.get('exports', {}).get('export_choice_validators', {})) > 0 and k != 'licenses')
                },
                'choice_attributes': {
                    k:v.get('exports', {}).get('export_choice_attributes') for k,v in self.smp_exports_map.items()
                    if (len(v.get('exports', {}).get('export_choice_attributes', {})) > 0 and k != 'licenses')
                }
            }
            
            license_export_choices = {}
            license_ids = get_project_license_ids(self.project, self.snapshot)
            license_count = len(license_ids)
            if license_count == 1:
                key = f'license_{license_ids[0].lower().replace("-", "_")}'
                license_export_choices[key] = ('False,LICENSE', ('LICENSE', _('File path')), key)
            elif license_count > 1:
                for l in license_ids:
                    key = f'license_{l.lower().replace("-", "_")}'
                    license_export_choices[key] = (
                        f'False,LICENSE_{l.replace("-", "_")}', 
                        (f'LICENSE_{l.replace("-", "_")}', _('File path')), 
                        key
                    )
            
            smp_export_choices.get('choices', []).extend(license_export_choices.values())

            for k in ['choice_validators', 'choice_attributes']:
                license_values = {
                    key:self.smp_exports_map.get('licenses', {}).get('exports', {}).get(f'export_{k}')
                    for key in license_export_choices.keys()
                }
                smp_export_choices.get(k, {}).update(license_values)
        
        smp_export_choice_keys = [c[2] for c in smp_export_choices.get('choices', [])]
        self.smp_export_choice_keys = smp_export_choice_keys

        return smp_export_choices

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
            exports, render_function, kwargs = self.smp_exports_map['licenses'].values()
            kwargs['choice'] = choice.replace('license_', '')
        else:
            exports, render_function, kwargs = self.smp_exports_map[choice].values()
        
        response = render_function(self.request, self.project, self.snapshot, **kwargs)
        return response
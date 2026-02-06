# rdmo-plugins-maus

This repo implements four plugins for Software Management Plan (SMP) projects in [RDMO](https://github.com/rdmorganiser/rdmo):

* a README export plugin, which creates a README.md file with the data in an SMP project
* a CITATION export plugin, which creates a CITATION.cff file with the data in an SMP project
* a LICENSE export plugin, which creates a LICENSE file or a licenses.zip file with the license(s) chosen for an SMP project
* an SMP Report export plugin, which creates an html file with all answers of an SMP project, displayed as a report

This repo also implements an SMPExportMixin class, which can be used by other [export plugins](https://rdmo.readthedocs.io/en/latest/plugins/#project-export-plugins). This SMPExportMixin class offers SMP-specific export options and their content. An example implementation is the [GitLabExportProvider](https://github.com/MPDL/rdmo-plugins-gitlab/tree/dev).

Furthermore, you will find a custom field "MultivalueCheckboxMultipleChoiceField" that displays choices similar to django's MultipleChoiceField with a CheckboxSelectMultiple widget. The difference to the built-in field is, that you can optionally have an extra text field for each choice, in case you need further text input. With this custom field you can also sort selected choices. For details, check out the [Field's docstring](https://github.com/MPDL/rdmo-plugins-maus/tree/main/rdmo_maus/forms/custom_fields.py) and for an example implementations take a look at the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py) and [GitHubImportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/imports.py) or try them out at our [demo RDMO instance](https://demo-rdmo.mpdl.mpg.de/).


## Setup

1. Install the plugin in your RDMO virtual environment using pip (directly from GitHub):

        ```bash
        pip install git+https://github.com/MPDL/rdmo-plugins-maus
        ```

2. For the CITATION export plugin, add "plain" to EXPORT_FORMATS in `config/settings/local.py`:

        ```python
        EXPORT_FORMATS = (
            ...
            ('plain', _('Plain Text'))
        )
        ```

3. For the export plugins, add the plugins to PROJECT_EXPORTS in `config/settings/local.py`:

        ```python
        PROJECT_EXPORTS += [
            ('smp-readme', _('README'), 'rdmo_maus.exports.smp_exports.SMPReadmeExport'),
            ('smp-citation', _('CITATION'), 'rdmo_maus.exports.smp_exports.SMPCitationExport'),
            ('smp-license', _('LICENSE'), 'rdmo_maus.exports.smp_exports.SMPLicenseExport'),
            ('smp-report', _('SMP Report'), 'rdmo_maus.exports.smp_exports.SMPReportExport')
        ]
        ```

4. For the README, CITATION and SMP Report export plugins, import the views needed in your RDMO instance. The views are "view-smp-citation.xml", "view-smp-readme.xml" and "view-smp-report.xml" and can be found in our [forked rdmo-catalog](https://github.com/MPDL/rdmo-catalog/tree/MPG-catalogues/rdmorganiser/views).

5. [Optional] These plugins are SMP-specific, and do not work properly for other catalogues. If a user clicks on one of them, they will be informed that the plugin only works for SMP projects. However, with the following adaptations, these plugins will only be shown to the user if the project has an SMP catalogue:

    5.1 [Optional] Add these lines in `rdmo.core.settings.py`:

        ```python
        SETTINGS_EXPORT += ['SMP_PROJECT_EXPORTS']

        SMP_PROJECT_EXPORTS = []
        ```

    5.2 [Optional] Modify this part of the code in `rdmo.projects.templates.projects.project_detail_sidebar.html`:

        ```html
        {% has_perm 'projects.export_project_object' request.user project as can_export_project %}
        {% if settings.PROJECT_EXPORTS and can_export_project %}
        <h2 id="export-project">{% trans 'Export' %}</h2>

        <ul class="list-unstyled">
            {% for key, label, class in settings.PROJECT_EXPORTS %}
            {% if key not in settings.SMP_PROJECT_EXPORTS or project.catalog.uri_path == 'smp' %} # !!! NEW LINE !!!
            <li>
                <a href="{% url 'project_export' project.pk key %}" target="_blank">
                    {{ label }}
                </a>
            </li>
            {% endif %} # !!! NEW LINE !!!
            {% endfor %}
        </ul>
        {% endif %}
        ```

    5.3 [Optional] Add the export plugin keys to SMP_PROJECT_EXPORTS in `config/settings/local.py`:

        ```python
        SMP_PROJECT_EXPORTS += ['smp-readme', 'smp-citation', 'smp-license', 'smp-report']
        ```

## Usage

### Export plugins

For SMP projects, users can export custom files (README, CITATION, LICENSE, and SMP report) created with the SMP project's data.

### SMPExportMixin

This repo also implements an SMPExportMixin class, which can be used by other [export plugins](https://rdmo.readthedocs.io/en/latest/plugins/#project-export-plugins). This SMPExportMixin class offers SMP-specific export options (README, CITATION, LICENSE, and SMP report) and their content. An example implementation is the [GitLabExportProvider](https://github.com/MPDL/rdmo-plugins-gitlab/tree/dev).

### Custom field "MultivalueCheckboxMultipleChoiceField"

1. Import the field in your form with `from rdmo_maus.forms.custom_fields import MultivalueCheckboxMultipleChoiceField`

2. Define one of your fields with this custom field:

```
my_multiple_choices = MultivalueCheckboxMultipleChoiceField(
        label='My Sortable Multiple Choices',
        sortable=True
        choices=[
            ('True,value-text-field', ('checkbox-label', 'text-label'), 'choice-1'), 
            ('False', 'single-checkbox-label', 'choice-2')
        ]
    )
```
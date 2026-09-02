# rdmo-plugins-maus

This repo implements five plugins for Software Management Plan (SMP) projects in [RDMO](https://github.com/rdmorganiser/rdmo):

* a README export plugin, which creates a README.md file with the data in an SMP project
* a CITATION export plugin, which creates a CITATION.cff file with the data in an SMP project
* a CodeMeta export plugin, which creates a codemeta.json file with the data in an SMP project
* a LICENSE export plugin, which creates a LICENSE file or a licenses.zip file with the license(s) chosen for an SMP project
* an SMP Report export plugin, which creates a pdf file with all answers of an SMP project, displayed as a report

This repo also implements two mixin classes (SMPExportMixin, SMPRepoImportMixin), which can be used by other [export plugins](https://rdmo.readthedocs.io/en/latest/plugins/#project-export-plugins) or [import plugins](https://rdmo.readthedocs.io/en/latest/plugins/index.html#project-import-plugins). These classes offer SMP-specific export and import options. An example implementation for an export plugin is the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py), and for an import plugin: [GitHubImportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/imports.py)

Furthermore, you will find two custom fields with their respective custom widgets.
- MultivalueCheckboxMultipleChoiceField
- ChoiceFieldWithOther

The first custom field is "MultivalueCheckboxMultipleChoiceField" and displays choices similar to django's MultipleChoiceField with a CheckboxSelectMultiple widget. The difference to the built-in field is, that you can optionally have an extra text field for each choice, in case you need further text input. With this custom field you can also sort selected choices. For details, check out the [Field's docstring](https://github.com/MPDL/rdmo-plugins-maus/tree/main/rdmo_maus/forms/custom_fields.py) and for example implementations take a look at the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py) and [GitHubImportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/imports.py) or try them out at our [demo RDMO instance](https://demo-rdmo.mpdl.mpg.de/).

The second custom field is "ChoiceFieldWithOther" and displays choices as radio buttons. It includes a last "other" choice with an input text field for free user input. For example implementations take a look at the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py) or the [GitLabExportProvider](https://github.com/MPDL/rdmo-plugins-gitlab/blob/dev/rdmo_gitlab/providers/exports.py) or try them out at our [demo RDMO instance](https://demo-rdmo.mpdl.mpg.de/).


## Setup

1. Install the plugin in your RDMO virtual environment using pip (directly from GitHub):

        ```bash
        pip install git+https://github.com/MPDL/rdmo-plugins-maus
        ```

2. Add "plain" and "pdf" to EXPORT_FORMATS in `config/settings/local.py`:

        ```python
        EXPORT_FORMATS = (
            ...
            ('plain', _('Plain Text')),
            ('pdf', _('PDF')),
        )
        ```

3. For the export plugins, add the plugins to PROJECT_EXPORTS in `config/settings/local.py`:

        ```python
        PROJECT_EXPORTS += [
            ('smp-readme', _('README'), 'rdmo_maus.exports.smp_exports.SMPReadmeExport'),
            ('smp-citation', _('CITATION'), 'rdmo_maus.exports.smp_exports.SMPCitationExport'),
            ('smp-codemeta', _('CodeMeta'), 'rdmo_maus.exports.smp_exports.SMPCodeMetaExport'),
            ('smp-license', _('LICENSE'), 'rdmo_maus.exports.smp_exports.SMPLicenseExport'),
            ('smp-report', _('SMP Report'), 'rdmo_maus.exports.smp_exports.SMPReportExport')
        ]
        ```

4. For the README, CITATION, CodeMeta and SMP Report export plugins, import the views needed in your RDMO instance. The views are "view-smp-citation.xml", "view-smp-codemeta.xml", "view-smp-readme.xml" and "view-smp-report.xml" and can be found in our [forked rdmo-catalog](https://github.com/MPDL/rdmo-catalog/tree/MPG-catalogues/rdmorganiser/views).

## Usage

### Export plugins

For SMP projects, users can export custom files (README, CITATION, CodeMeta, LICENSE, and SMP report) created with the SMP project's data.

### SMPExportMixin and SMPRepoImportMixin

This repo also implements two mixin classes (SMPExportMixin, SMPRepoImportMixin), which can be used by other [export plugins](https://rdmo.readthedocs.io/en/latest/plugins/#project-export-plugins) or [import plugins](https://rdmo.readthedocs.io/en/latest/plugins/index.html#project-import-plugins). These classes offer SMP-specific export and import options. An example implementation for an export plugin is the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py), and for an import plugin: [GitHubImportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/imports.py)

### Custom field "MultivalueCheckboxMultipleChoiceField"

For details, check out the [Field's docstring](https://github.com/MPDL/rdmo-plugins-maus/tree/main/rdmo_maus/forms/custom_fields.py) and for example implementations take a look at the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py) and [GitHubImportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/imports.py) or try them out at our [demo RDMO instance](https://demo-rdmo.mpdl.mpg.de/).

1. Import the field in your form with `from rdmo_maus.forms.custom_fields import MultivalueCheckboxMultipleChoiceField`

2. Define one of your fields with this custom field:

        ```python
        my_multiple_choices = MultivalueCheckboxMultipleChoiceField(
                label='My Sortable Multiple Choices',
                sortable=True,
                include_select_all_choice=True,
                choices=[
                    ('True,value-text-field', ('checkbox-label', 'text-label'), 'choice-1'),
                    ('False', 'single-checkbox-label', 'choice-2')
                ]
            )
        ```

3. Include form.media in your form template:

        ```html
        <head>
        ...

        {{ form.media }}

        </head>
        ```

### Custom field "ChoiceFieldWithOther"

For example implementations take a look at the [GitHubExportProvider](https://github.com/MPDL/rdmo-plugins-github/blob/dev/rdmo_github/providers/exports.py) or the [GitLabExportProvider](https://github.com/MPDL/rdmo-plugins-gitlab/blob/dev/rdmo_gitlab/providers/exports.py) or try them out at our [demo RDMO instance](https://demo-rdmo.mpdl.mpg.de/).

1. Import the field in your form with `from rdmo_maus.forms.custom_fields import ChoiceFieldWithOther`

2. Define one of your fields with this custom field:

        ```python
        my_radio_buttons = ChoiceFieldWithOther(
                label='My Radio Button Choices with Other',
                choices=[
                    ('choice-1', 'Choice 1'),
                    ('choice-2', 'Choice 2')
                ]
            )
        ```

3. Include form.media in your form template:

        ```html
        <head>
        ...

        {{ form.media }}

        </head>
        ```

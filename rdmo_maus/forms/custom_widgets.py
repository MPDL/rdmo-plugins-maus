from django import forms
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

class MultivalueCheckboxWidget(forms.MultiWidget):
    def __init__(self, simple_checkbox=False, attrs=None):
        widgets = {
            'checkbox': forms.CheckboxInput()
        }

        if not simple_checkbox:
            widgets['text'] = forms.TextInput() 

        super().__init__(widgets, attrs)

    def decompress(self, value):
        '''Transform input value to a list with the correctly typed value for each subwidget:
            - a boolean value for the checkbox
            - (optionally) a string value for the text
        '''
        boolean_value = {'False': False, 'True': True}
        if isinstance(value, str):
            splitted_value = value.split(',')
            splitted_value[0] = boolean_value[splitted_value[0]]
            return splitted_value
        
        return [False, '']
    
    def get_context(self, name, value, checkbox_label, text_label, attrs, extra_attrs=None):
        '''Create context for MultivalueCheckboxMultipleChoiceWidget.option_template_name. '''
        
        context = super().get_context(name, value, attrs)
        # value is a list/tuple of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, (list, tuple)):
            value = self.decompress(value)

        final_attrs = context['widget']['attrs']
        subwidgets = []
        for i, (widget_name, widget) in enumerate(
            zip(self.widgets_names, self.widgets)
        ):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            
            extra_widget_attrs = extra_attrs.get(widget_name.strip('_'), {}) if isinstance(extra_attrs, dict) else {}
            
            widget_attrs = final_attrs.copy()
            widget_attrs.update(extra_widget_attrs)
            
            widget_context = widget.get_context(name + widget_name, widget_value, widget_attrs)['widget']
            if widget_name == '_text':
                widget_context.update({'label': text_label})
            if widget_name == '_checkbox':
                widget_context.update({'label': checkbox_label})
            
            subwidgets.append(widget_context)
        
        context['widget']['subwidgets'] = subwidgets
        return context
    

class MultivalueCheckboxMultipleChoiceWidget(forms.SelectMultiple):
    '''
    A multiple choice widget with multivalue checkboxes as choices. 
    Widget for MultivalueCheckboxMultipleChoiceField.
    
    ###########
    # CHOICES #
    ###########
    
    Each choice consists of one or two fields:
    - a checkbox field with a label 
    - (optionally) a text input field with a label

    choices (list[tuple[str, tuple[str] | str, str]]) = [(values, labels, key), ...] with:

    1. values (str): comma-separated values for each choice. 
    First value is required and is the starting value for the checkbox (as a string: 'True' or 'False'), 
    second value is optional and is the starting value for the text.
    Examples of valid values:
    - 'False,my-text' -> checkbox's starting value is False, text's starting value is 'my-text'
    - 'True,' -> checkbox's starting value is True, text's starting value is ''
    - 'True' -> checkbox's starting value is True, text's starting value does NOT exist (no comma)
    
    2. labels (str | tuple[str]): a string or a one or two-value tuple with the checkbox and text field labels (str).
    First value is required, second is optional.
    Examples of valid labels:
    - ('Checkbox label', 'Text label')
    - ('one value tuple with checkbox label',)
    - 'string label for checkbox'

    3. key (str): choice key.
    Examples:
    - 'choice_1'
    - 'pdf-export'

    ############
    # SORTABLE #
    ############

    Per default, choices are displayed and processed as passed. Selected choices can be sortable if the parameter
    SORTABLE equals True when initializing the field (preferable: MultivalueCheckboxMultipleChoiceField(..., sortable=True))
    or the widget (MultivalueCheckboxMultipleChoiceWidget(..., sortable=True)).

    #############################
    # INCLUDE_SELECT_ALL_CHOICE #
    #############################

    Per default, each choice must be individually selected. If the parameter INCLUDE_SELECT_ALL_CHOICE equals True when
    initializing the field (preferable: MultivalueCheckboxMultipleChoiceField(..., include_select_all_choice=True)) or the
    widget (MultivalueCheckboxMultipleChoiceWidget(..., include_select_all_choice=True)), the first 
    displayed choice is a 'Select all' choice. Clicking this choice will set all other choices as selected.

    #####################
    # CHOICE ATTRIBUTES #
    #####################

    Attributes common to all choices can be passed as usual:
    - MultivalueCheckboxMultipleChoiceWidget(..., attrs=attrs).
    
    Choice attributes can also be passed as follows: 
    - MultivalueCheckboxMultipleChoiceWidget(..., choice_attributes=choice_attributes) where:

    - choice_attributes (dict[choice_key, dict['checkbox'|'text', attrs_dict]]) is a dictionary with choice_keys 
    as keys and for values dictionaries with attributes for the checkbox widget and/or the text widget. choice_attributes 
    only need to contain choice_keys of choices with extra attributes, and only the widget ('checkbox' or 'text') that
    needs extra attributes must be included in the inner dictionary.
    
    Examples:

    If these are the choices = ((values_1, labels_1, 'choice_1'), (values_2, labels_2, 'choice_2'), (values_3, labels_3, 'choice_3')),
    these would be valid choice_attributes:
    - choice_attributes = {
        'choice_1': {
            'checkbox': {'onchange': changeHandler()}
        },
        'choice_2': {
            'checkbox': {'onchange': changeHandler()},
            'text': {'oninput': inputHandler(), 'style': 'background-color: blue;'}
        }
    }

    ###################
    # CHOICE WARNINGS #
    ###################

    Similar to choice_attributes, choice_warnings can also be passed to the widget:
    MultivalueCheckboxMultipleChoiceWidget(..., choice_warnings=choice_warnings)

    choice_warnings only need to contain choice_keys of choices with warnings. If passed, these warnings 
    appear below the corresponding choice like errors but they will not prevent form submission.

    Examples:

    If these are the choices = ((values_1, labels_1, 'choice_1'), (values_2, labels_2, 'choice_2'), (values_3, labels_3, 'choice_3')),
    these would be valid choice_warnings:
    - choice_warnings (dict[str, list[str]]) = {
        'choice_2': ['Warning_1 for choice_2', 'Warning_2 for choice_2'],
        'choice_3': ['Single warning for choice_3']
    }

    '''
    option_inherits_attrs = True
    errors = {}
    option_template_name = 'plugins/multivalue_checkbox.html'
    template_name = 'plugins/multivalue_checkbox_multiple_choice.html'
    select_all_choice = ('False', _('Select all'), 'select_all_choice')

    _choice_keys = []
    _choice_widgets = {}
    _choice_attributes = {}
    select_all_choice_attributes = {
        'checkbox': {'onchange': 'toggleAllChoices(this)'}
    }
    default_choice_attributes = {
        'checkbox': {'onchange': 'toggleChoiceAttributesVisibility(this)'}, 
        'text': {'oninput': 'hideChoiceWarningMessages(this)', 'class': 'form-control multivalue-checkbox-text-input'}
    }
    
    def __init__(self, *, sortable=False, include_select_all_choice=False, choice_attributes={}, choice_warnings={}, **kwargs):
        '''
        MultivalueCheckboxMultipleChoiceWidget.__init__

        :param list[tuple[str, tuple[str] | str, str]] choices: List of choices. Each choice is a tuple of value(s) (comma-separated str), label(s) (tuple[str] or str), and a key (str). Check out the class docstring for details.
        :param bool include_select_all_choice: If True, first choice will be a 'Select all' choice
        :param bool sortable: If True, selected choices will be sortable
        :param dict[str, dict['checkbox'|'text', list[validators]]] choice_attributes: choice-specific validators for checkbox and/or text choice subfields. Check out the class docstring for details.
        :param dict[str, list[str]] choice_warnings: choice-specific lists of warnings. Check out the class docstring for details.
        :param kwargs: rest of keyword arguments of django's SelectMultiple widget
        '''
        
        self.include_select_all_choice = include_select_all_choice
        self.sortable = sortable
        self.choice_warnings = choice_warnings
        self.choice_attributes = choice_attributes

        super().__init__(**kwargs)

    class Media:
        css = {
            'all': [static('plugins/css/multivalue_checkbox_multiple_choice.css')]
        }
        js = [format_html('<script src="{}" defer ></script>', static('plugins/js/multivalue_checkbox_multiple_choice.js'))]
    
    @property
    def choices(self):
        return self._choices
    
    @choices.setter
    def choices(self, new_choices):
        first_choice = new_choices[0] if len(new_choices) > 0 else None
        if (
            self.include_select_all_choice and 
            (first_choice is not None and first_choice[2] != self.select_all_choice[2])
        ):
            new_choices = [self.select_all_choice, *new_choices]
        self._choices = new_choices
        self.choice_widgets = new_choices
        self.choice_keys = new_choices

    @property
    def choice_widgets(self):
        return self._choice_widgets
    
    @choice_widgets.setter
    def choice_widgets(self, new_choices):
        new_choice_widgets = {}

        for c in new_choices:
            simple_checkbox = False
            
            values = c[0].split(',')
            choice_key = c[2]
            if isinstance(values, list) and len(values) == 1:
                simple_checkbox = True

            new_choice_widgets[choice_key] = MultivalueCheckboxWidget(simple_checkbox=simple_checkbox)

        self._choice_widgets = new_choice_widgets
    
    @property
    def choice_keys(self):
        return self._choice_keys
    
    @choice_keys.setter
    def choice_keys(self, new_choices):
        new_choice_keys = [c[2] for c in new_choices]
        self._choice_keys = new_choice_keys

    @property
    def choice_attributes(self):
        return self._choice_attributes
    
    @choice_attributes.setter
    def choice_attributes(self, new_attributes):
        self._choice_attributes = new_attributes

    def sort_choices(self, data, name):
        selected_choices = [k for k,v in data.items() if (k.startswith(name) and k.endswith('_checkbox') and 'on' in v)]
        sorted_choice_keys = [c.removeprefix(f'{name}_').removesuffix('_checkbox') for c in selected_choices]

        for k in self.choice_keys:
            if k not in sorted_choice_keys:
                sorted_choice_keys.append(k)

        sorted_choices = []
        for k in sorted_choice_keys:
            choice = next((c for c in self.choices if c[2] == k), None)
            if choice is not None:
                sorted_choices.append(choice)

        return sorted_choice_keys, sorted_choices

    def optgroups(self, name, value, attrs=None):
        '''Return a list of choices for this widget.
        Each choice consists of a multi widget with a checkbox and a text.
        '''
        
        transformed_value = []
        selected_option_keys = []
        for v in value:
            v_list = v.split(',')
            selected_option_keys.append(v_list[0])
            transformed_v = f'True,{v_list[1]}' if len(v_list) > 1 else 'True'
            transformed_value.append(transformed_v)

        current_errors = {k: v for k, v in self.errors.items() if k in selected_option_keys}
        self.errors = current_errors

        groups = []

        for index, (option_value, option_labels, option_key) in enumerate(self.choices):
            i = selected_option_keys.index(option_key) if option_key in selected_option_keys else None
            option_value = transformed_value[i] if i is not None else option_value
            choice_widget = self.choice_widgets[option_key]
            decompressed_option_value = choice_widget.decompress(option_value)
            
            selected = self.allow_multiple_selected and decompressed_option_value[0]
            
            option_name = f'{name}_{option_key}'
            
            if self.include_select_all_choice:
                index = option_key if option_key == 'select_all_choice' else index - 1

            groups.append(self.create_option(
                choice_widget,
                option_name,
                option_value,
                option_labels,
                option_key,
                selected,
                index,
                attrs=attrs,
            ))

        return groups

    def create_option(
        self, widget, name, value, labels, key, selected, index, attrs=None
    ):
        '''Create a choice consisting of a multi widget with a checkbox and a text. '''  
        
        index = str(index)
        option_attrs = (
            self.build_attrs(self.attrs, attrs) if self.option_inherits_attrs else {}
        )

        extra_option_attrs = (
            self.select_all_choice_attributes 
            if key == 'select_all_choice' 
            else self.choice_attributes.get(key, {})
        )
        if key != 'select_all_choice':
            for k, v in self.default_choice_attributes.items():
                if k in extra_option_attrs.keys():
                    extra_option_attrs[k].update(v)
                else:
                    extra_option_attrs[k] = v

        if 'id' in option_attrs:
            checkbox_id = '%s_%s' % (option_attrs['id'], index)
            extra_option_attrs['checkbox'].update({'id': checkbox_id})
        
            text_id = '%s_%s' % (f'{option_attrs["id"]}_text', index)
            extra_option_attrs['text'].update({'id': text_id})

            option_attrs = {}

        if selected:
            option_attrs.update(self.checked_attribute)

        checkbox_label = text_label = ''
        if isinstance(labels, tuple):
            checkbox_label = labels[0]
            text_label = labels[1] if len(labels) > 1 else ''
        else:
            checkbox_label = labels

        option_context = widget.get_context(
            name, value, checkbox_label, text_label, option_attrs, extra_option_attrs
        )
        option_errors = self.errors[key] if key in self.errors.keys() else None
        option_warnings = self.choice_warnings[key] if key in self.choice_warnings.keys() else None

        return {
            'name': name,
            'index': index,
            'value': value,
            'errors': option_errors,
            'warnings': option_warnings,
            'subwidgets': option_context['widget']['subwidgets'],
            'selected': selected,
            'template_name': self.option_template_name,
        }
    
    def value_from_datadict(self, data, files, name):
        if self.sortable:
            self.choice_keys, self.choices = self.sort_choices(data, name)
        
        value = []
        for multiwidget_name in self.choice_keys:
            choice_widget = self.choice_widgets[multiwidget_name]
            multiwidget_value = choice_widget.value_from_datadict(data, files, f'{name}_{multiwidget_name}')
            
            if multiwidget_value[0]:
                choice_value = multiwidget_name if len(multiwidget_value) == 1 else f'{multiwidget_name},{multiwidget_value[1]}'
                value.append(choice_value)

        return value
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['sortable'] = self.sortable
        
        if self.sortable and self.include_select_all_choice:
            widget_optgroups = context['widget']['optgroups']
            select_all_option = widget_optgroups[0]
            widget_optgroups = widget_optgroups[1:]
            
            context['widget']['select_all_option'] = select_all_option
            context['widget']['optgroups'] = widget_optgroups

        return context
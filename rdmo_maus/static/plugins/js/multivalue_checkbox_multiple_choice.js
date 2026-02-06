const draggables = document.querySelectorAll('.drag-icon');
const droppable = document.querySelector('.selected');
const defaultZone = document.querySelector('.unselected');

function moveChoice(droppable, index, selected) {
  const choiceBlock = document.getElementById(index);
  let dragIcon = document.getElementById(`drag_icon_${index}`)
  
  if (selected == true) {
    droppable.appendChild(choiceBlock);
    dragIcon.draggable = true;
    dragIcon.style.display = 'flex';
  } else {
    defaultZone.appendChild(choiceBlock);
    dragIcon.draggable = false;
    dragIcon.style.display = 'none';
  }
}

function toggleAllChoices(selectAllCheckbox) {
  const selectAllCheckboxId = selectAllCheckbox.id;
  // selectAllCheckbox.id = fieldId + '_select_all_choice'
  const choiceIdPrefix = selectAllCheckboxId.replace('_select_all_choice', '');
  // match all checkboxes of the field, excluding selectAllCheckbox itself and text inputs
  const allChoices = document.querySelectorAll(  
    `[id^="${choiceIdPrefix}"]:not([id="${selectAllCheckboxId}"],[id^="${choiceIdPrefix}_text"])`
  )
  allChoices.forEach((choice, i) => {
    choice.checked = selectAllCheckbox.checked;
    
    let file_path = document.getElementById(`id_file_path_${i}`);
    if (file_path) {
        file_path.style.display = selectAllCheckbox.checked ? 'flex' : 'none';
    }

    let warning_messages = document.getElementById(`id_warnings_${i}`);
    if (warning_messages) {
        warning_messages.style.display = selectAllCheckbox.checked ? 'inline' : 'none';
    }

    let error_messages = document.getElementById(`id_errors_${i}`);
    if (error_messages) {
      error_messages.style.display = selectAllCheckbox.checked ? 'block' : 'none';
    }

    if (droppable) {
      moveChoice(droppable, i, selectAllCheckbox.checked);
    }
  });
}

function toggleChoiceAttributesVisibility(checkbox) {
    const index = checkbox.id.split('_').findLast((e) => e)
    
    let file_path = document.getElementById(`id_file_path_${index}`);
    if (file_path) {
        file_path.style.display = checkbox.checked ? 'flex' : 'none';
    }

    let warning_messages = document.getElementById(`id_warnings_${index}`);
    if (warning_messages) {
        warning_messages.style.display = checkbox.checked ? 'inline' : 'none';
    }

    let error_messages = document.getElementById(`id_errors_${index}`);
    if (error_messages) {
      error_messages.style.display = checkbox.checked ? 'block' : 'none';
    }

    if (droppable) {
      moveChoice(droppable, index, checkbox.checked)
    }
}

function hideChoiceWarningMessages(text) {
    const index = text.id.split('_').findLast((e) => e)

    let duration = 1000;
    clearTimeout(text._timer);
    text._timer = setTimeout(()=>{
        let warning_messages = document.getElementById(`id_warnings_${index}`);
        if (warning_messages) {
            warning_messages.style.display = 'none';
        }
    }, duration);
}

draggables.forEach((dragIcon) => {
  const index = dragIcon.id.replace('drag_icon_', '');
  let choiceBlock = document.getElementById(index);
  
  /* DRAG AND DROP */
  dragIcon.addEventListener('dragstart', () => {
    choiceBlock.classList.add('is-dragging');
  });
  dragIcon.addEventListener('dragend', () => {
    choiceBlock.classList.remove('is-dragging');
  });

  /* TOUCH */
  dragIcon.addEventListener('touchstart', () => {
    const droppablePosition = droppable.getBoundingClientRect();
    choiceBlock.classList.add('is-dragging');
    
    dragIcon.addEventListener('touchmove', (eve) => {      
      eve.preventDefault();

      let nextX = eve.changedTouches[0].clientX;
      let nextY = eve.changedTouches[0].clientY;

      if ( // as long as touchmove happens inside of droppable
        nextX >= droppablePosition.left & 
        nextX <= droppablePosition.right &
        nextY >= droppablePosition.top &
        nextY <= droppablePosition.bottom
      ) {
        const bottomChoiceBlock = insertAboveTask(droppable, nextY);
        
        if (!bottomChoiceBlock) {
          droppable.appendChild(choiceBlock);
        } else {
          droppable.insertBefore(choiceBlock, bottomChoiceBlock);
        }
      }
    });

    dragIcon.addEventListener('touchend', () => {
      choiceBlock.classList.remove('is-dragging');
    });
  
  });
});


/* DRAG AND DROP */
droppable?.addEventListener('dragover', (e) => {
    e.preventDefault();

    const bottomChoiceBlock = insertAboveTask(droppable, e.clientY);
    const curChoiceBlock = document.querySelector('.is-dragging');
    
    if (!bottomChoiceBlock) {
      droppable.appendChild(curChoiceBlock);
    } else {
      droppable.insertBefore(curChoiceBlock, bottomChoiceBlock);
    }

});

/* DRAG AND DROP and TOUCH */
const insertAboveTask = (zone, mouseY) => {
  const els = zone.querySelectorAll('.choice-block:not(.is-dragging)');
  let closestChoiceBlock = null;
  let closestOffset = Number.NEGATIVE_INFINITY;

  els.forEach((choiceBlock) => {
    const { top } = choiceBlock.getBoundingClientRect();
    const offset = mouseY - top;
    
    if (offset < 0 && offset > closestOffset) {
      closestOffset = offset;
      closestChoiceBlock = choiceBlock;
    }
  });

  return closestChoiceBlock;
};
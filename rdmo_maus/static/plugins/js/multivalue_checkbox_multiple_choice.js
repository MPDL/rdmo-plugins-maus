const draggables = document.querySelectorAll('.drag-icon')
const droppable = document.querySelector('.droppable')

function toggleAllChoices(selectAllCheckbox) {
  const selectAllCheckboxId = selectAllCheckbox.id
  const fieldId = selectAllCheckboxId.replace('_checkbox_select_all_choice', '')
  // match all checkboxes of the field, excluding selectAllCheckbox itself and text inputs
  const allChoices = document.querySelectorAll(
    `[id^="${fieldId}_checkbox"]:not([id="${selectAllCheckboxId}"],[id^="${fieldId}_text"])`
  )
  allChoices.forEach((choice, i) => {
    choice.checked = selectAllCheckbox.checked

    let filePath = document.getElementById(`${fieldId}_file_path_${i}`)
    if (filePath) {
      filePath.style.display = selectAllCheckbox.checked ? 'flex' : 'none'
    }

    let warningMessages = document.getElementById(`${fieldId}_warnings_${i}`)
    if (warningMessages) {
      warningMessages.style.display = selectAllCheckbox.checked ? 'inline' : 'none'
    }

    let errorMessages = document.getElementById(`${fieldId}_errors_${i}`)
    if (errorMessages) {
      errorMessages.style.display = selectAllCheckbox.checked ? 'block' : 'none'
    }
  })
}

function toggleChoiceAttributesVisibility(checkbox) {
  const fieldId = `${checkbox.id.split('_')[0]}_${checkbox.id.split('_')[1]}`
  const index = checkbox.id.split('_').findLast((e) => e)

  let selectAllCheckbox = document.getElementById(`${fieldId}_checkbox_select_all_choice`)
  if (selectAllCheckbox) {
    // if at least one choice is dropped, then selectAllCheckbox must turn false
    if (!checkbox.checked) {
      selectAllCheckbox.checked = false
    }

    // if all choices are selected, then selectAllCheckbox must turn true
    // match all checkboxes of the field, excluding selectAllCheckbox itself and text inputs
    let allChoices = document.querySelectorAll(
      `[id^="${fieldId}_checkbox"]:not([id="${fieldId}_checkbox_select_all_choice"],[id^="${fieldId}_text"])`
    )
    let allChoicesChecked = [...allChoices].map(choice => choice.checked).every(value => value === true)
    if (allChoicesChecked) {
      selectAllCheckbox.checked = true
    }

  }

  let filePath = document.getElementById(`${fieldId}_file_path_${index}`)
  if (filePath) {
    filePath.style.display = checkbox.checked ? 'flex' : 'none'
  }

  let warningMessages = document.getElementById(`${fieldId}_warnings_${index}`)
  if (warningMessages) {
    warningMessages.style.display = checkbox.checked ? 'inline' : 'none'
  }

  let errorMessages = document.getElementById(`${fieldId}_errors_${index}`)
  if (errorMessages) {
    errorMessages.style.display = checkbox.checked ? 'block' : 'none'
  }

  if (droppable && !checkbox.checked) {
    const choiceBlock = document.getElementById(`${fieldId}_choice_block_${index}`)
    droppable.appendChild(choiceBlock)
  }
}

function hideChoiceWarningMessages(text) {
  const fieldId = `${text.id.split('_')[0]}_${text.id.split('_')[1]}`
  const index = text.id.split('_').findLast((e) => e)

  let duration = 1000
  clearTimeout(text._timer)
  text._timer = setTimeout(()=>{
    let warningMessages = document.getElementById(`${fieldId}_warnings_${index}`)
    if (warningMessages) {
      warningMessages.style.display = 'none'
    }
  }, duration)
}

draggables.forEach((dragIcon) => {
  const fieldId = `${dragIcon.id.split('_')[0]}_${dragIcon.id.split('_')[1]}`
  const index = dragIcon.id.split('_').findLast((e) => e)
  let choiceBlock = document.getElementById(`${fieldId}_choice_block_${index}`)

  /* DRAG AND DROP */
  dragIcon.addEventListener('dragstart', () => {
    choiceBlock.classList.add('is-dragging')
  })
  dragIcon.addEventListener('dragend', () => {
    choiceBlock.classList.remove('is-dragging')
  })

  /* TOUCH */
  dragIcon.addEventListener('touchstart', () => {
    const droppablePosition = droppable.getBoundingClientRect()
    choiceBlock.classList.add('is-dragging')

    dragIcon.addEventListener('touchmove', (eve) => {
      eve.preventDefault()

      let nextX = eve.changedTouches[0].clientX
      let nextY = eve.changedTouches[0].clientY

      if ( // as long as touchmove happens inside of droppable
        nextX >= droppablePosition.left &
        nextX <= droppablePosition.right &
        nextY >= droppablePosition.top &
        nextY <= droppablePosition.bottom
      ) {
        const bottomChoiceBlock = insertAboveTask(droppable, nextY)

        if (!bottomChoiceBlock) {
          droppable.appendChild(choiceBlock)
        } else {
          droppable.insertBefore(choiceBlock, bottomChoiceBlock)
        }
      }
    })

    dragIcon.addEventListener('touchend', () => {
      choiceBlock.classList.remove('is-dragging')
    })

  })
})


/* DRAG AND DROP */
droppable?.addEventListener('dragover', (e) => {
  e.preventDefault()

  const bottomChoiceBlock = insertAboveTask(droppable, e.clientY)
  const curChoiceBlock = document.querySelector('.is-dragging')

  if (!bottomChoiceBlock) {
    droppable.appendChild(curChoiceBlock)
  } else {
    droppable.insertBefore(curChoiceBlock, bottomChoiceBlock)
  }

})

/* DRAG AND DROP and TOUCH */
const insertAboveTask = (zone, mouseY) => {
  const els = zone.querySelectorAll('.choice-block:not(.is-dragging)')
  let closestChoiceBlock = null
  let closestOffset = Number.NEGATIVE_INFINITY

  els.forEach((choiceBlock) => {
    const { top } = choiceBlock.getBoundingClientRect()
    const offset = mouseY - top

    if (offset < 0 && offset > closestOffset) {
      closestOffset = offset
      closestChoiceBlock = choiceBlock
    }
  })

  return closestChoiceBlock
}

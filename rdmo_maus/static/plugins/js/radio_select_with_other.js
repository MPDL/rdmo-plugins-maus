function selectOtherOption(inputText) {
  let radioId = inputText.id.replace('text', 'radio')
  let radio = document.getElementById(radioId)
  radio.checked = true
}

function deselectOtherOption(radio) {
  let radioIdPrefix = radio.id.split('_').slice(0, -1).join('_')
  let allRadioChoices = document.querySelectorAll(
      `[id^="${radioIdPrefix}"]`
    )
  let textId = `${radioIdPrefix.replace('radio', 'text')}_${allRadioChoices.length - 1}`
  let text = document.getElementById(textId)
  if (text) {
    text.value = ''
  }
}

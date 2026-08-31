function selectRadioOption(inputText) {
    let radioId = inputText.id.replace('text', 'radio')
    let radio = document.getElementById(radioId)
    radio.checked = true
}
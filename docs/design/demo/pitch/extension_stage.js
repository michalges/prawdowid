const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const $ = (id) => document.getElementById(id)

async function moveCursor(x, y, durationMs = 500) {
  $('cursor').style.transitionDuration = `${durationMs}ms`
  $('cursor').style.left = `${x}px`
  $('cursor').style.top = `${y}px`
  await wait(durationMs + 40)
}

function wrapWords(element) {
  const words = element.textContent.trim().split(/\s+/)
  element.innerHTML = words.map((word) => `<span class="word">${word}</span>`).join(' ')
  return [...element.querySelectorAll('.word')]
}

window.stage = {
  async run(claim) {
    const words = wrapWords($('claim'))
    const first = words[0].getBoundingClientRect()
    await wait(500)
    await moveCursor(first.left - 2, first.top + 4, 700)
    for (const word of words) {
      word.classList.add('selected')
      const box = word.getBoundingClientRect()
      await moveCursor(box.right, box.top + 4, 70)
    }
    await wait(350)
    const last = words[words.length - 1].getBoundingClientRect()
    const menuLeft = last.right - 120
    const menuTop = last.bottom + 2
    Object.assign($('menu').style, { left: `${menuLeft}px`, top: `${menuTop}px` })
    await moveCursor(last.right - 120, last.top + 6, 250)
    $('menu').classList.add('visible')
    await wait(600)
    const item = $('menu-item').getBoundingClientRect()
    await moveCursor(item.left + 60, item.top + item.height / 2 - 4, 450)
    $('menu-item').classList.add('hover')
    await wait(450)
    $('menu').classList.remove('visible')
    $('popup').src = 'popup.html'
    await new Promise((resolve) => $('popup').addEventListener('load', resolve, { once: true }))
    await chrome.runtime.sendMessage({ kind: 'start_check', input: { type: 'text', text: claim }, label: claim })
    $('ext-icon').classList.add('active')
    $('badge').style.display = 'block'
    $('popup').classList.add('visible')
    await moveCursor(1000, 560, 600)
  },

  isResultShown() {
    return Boolean($('popup').contentDocument?.querySelector('.claim, .full-result'))
  },
}

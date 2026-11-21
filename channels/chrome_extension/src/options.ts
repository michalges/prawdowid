import { deleteSession, isServerHealthy } from './api.js'
import { getRequiredElement } from './dom.js'
import { clearSessionId, getNormalizedServerUrl, getOriginPattern, getServerUrl, setServerUrl } from './settings.js'
import { setCheckState } from './state.js'

const form = getRequiredElement('server-form', HTMLFormElement)
const serverInput = getRequiredElement('server-url', HTMLInputElement)
const serverStatus = getRequiredElement('server-status', HTMLElement)
const deleteButton = getRequiredElement('delete-data', HTMLButtonElement)
const deleteStatus = getRequiredElement('delete-status', HTMLElement)

void getServerUrl().then((serverUrl) => {
  serverInput.value = serverUrl
})

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  const serverUrl = getNormalizedServerUrl(serverInput.value)
  if (!serverUrl) {
    serverStatus.textContent = 'Podaj adres zaczynający się od https:// lub http://.'
    return
  }
  const isGranted = await chrome.permissions.request({ origins: [getOriginPattern(serverUrl)] })
  if (!isGranted) {
    serverStatus.textContent = 'Bez zgody na dostęp do tego adresu rozszerzenie nie połączy się z serwerem.'
    return
  }
  await setServerUrl(serverUrl)
  serverInput.value = serverUrl
  serverStatus.textContent = 'Zapisano. Sprawdzamy połączenie…'
  serverStatus.textContent = (await isServerHealthy(serverUrl))
    ? 'Zapisano. Serwer odpowiada.'
    : 'Zapisano, ale serwer nie odpowiada pod tym adresem.'
})

deleteButton.addEventListener('click', async () => {
  if (!confirm('Usunąć sprawdzenia z tego rozszerzenia z serwera Prawdowida?')) return
  try {
    await deleteSession(await getServerUrl())
    await clearSessionId()
    await setCheckState(null)
    deleteStatus.textContent = 'Usunęliśmy Twoje dane z serwera i z rozszerzenia.'
  } catch (error) {
    deleteStatus.textContent = error instanceof Error ? error.message : 'Nie udało się usunąć danych.'
  }
})

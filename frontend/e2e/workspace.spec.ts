import { expect, test, type Page } from '@playwright/test'

const station = { id: 'JC148', name: 'Bay St & Washington St', lat: 40.72022, lng: -74.03656, observations: 1377 }
const series = Array.from({ length: 108 }, (_, index) => ({
  timestamp: `2026-04-${String(26 + Math.floor(index / 24)).padStart(2, '0')} ${String(index % 24).padStart(2, '0')}:00:00`,
  actual: index % 7,
  gcn_gru: (index % 7) + 0.4,
  naive: (index + 6) % 7,
  seasonal_24h: index % 6,
}))

async function mockApi(page: Page) {
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let body: unknown = {}
    if (path === '/api/health') body = { status: 'ok', dataset_available: true, experiments_enabled: false }
    else if (path === '/api/stations') body = [station, { ...station, id: 'JC115', name: 'Grove St PATH', lat: 40.71941 }]
    else if (path === '/api/graph') body = { nodes: [station, { ...station, id: 'JC115', name: 'Grove St PATH', lat: 40.71941 }], edges: [{ source: 'JC148', target: 'JC115', weight: 25 }, { source: 'JC115', target: 'JC148', weight: 55 }] }
    else if (path === '/api/predictions') body = series
    else if (path === '/api/stations/JC148/predictions') body = { station, predictions: series }
    else if (path === '/api/metrics') body = [{ model: 'Naive', mae: .838, rmse: 2.138, source: 'extended_comparison.csv' }, { model: 'Saisonnier 24 h', mae: .816, rmse: 2.051, source: 'extended_comparison.csv' }, { model: 'GCN-GRU enrichi', mae: .989, rmse: 2.117, source: 'extended_comparison.csv' }]
    else if (path === '/api/experiments') body = { completed: [], tasks: [] }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
}

test('Graph Explorer recalculates visible connections', async ({ page }) => {
  await mockApi(page)
  await page.goto('/graph')
  await expect(page.getByTestId('visible-connection-count')).toHaveText('2')
  await page.getByLabel('Minimum trip count').fill('50')
  await expect(page.getByTestId('visible-connection-count')).toHaveText('1')
  await page.getByPlaceholder(/Rechercher/).fill('JC148')
  await page.getByRole('option', { name: /JC148/ }).click()
  await expect(page.getByPlaceholder(/Rechercher/)).toHaveValue(/Bay St & Washington St/)
})

test('Demand Forecasting selects a real station series', async ({ page }) => {
  await mockApi(page)
  await page.goto('/forecast')
  await page.getByLabel('Forecast station').selectOption('JC148')
  await page.getByLabel('Forecast period').selectOption('24')
  await expect(page.getByText('Bay St & Washington St', { exact: true })).toBeVisible()
  await expect(page.getByText('24 heures affichées')).toBeVisible()
  await expect(page.getByText('Saisonnier 24 h')).toBeVisible()
})

test('public Experiments Lab stays read-only', async ({ page }) => {
  await mockApi(page)
  await page.goto('/experiments')
  await expect(page.getByRole('button', { name: 'Lecture seule' })).toBeDisabled()
  await expect(page.getByText(/Mode public sécurisé/)).toBeVisible()
})

import { expect, test } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'
import type { SearchResponse } from '../src/types'

async function getMetadata(
  request: APIRequestContext,
): Promise<SearchResponse> {
  const response = await request.get('/api/listings')
  expect(response.ok()).toBe(true)
  return response.json()
}

function pageRange(page: number, pageSize: number, total: number) {
  return `Showing ${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`
}

test('all result pages fit common desktop viewports without scrolling', async ({
  page,
  request,
}, testInfo) => {
  const { pageSize, total, totalPages } = await getMetadata(request)
  for (const viewport of [
    { width: 1280, height: 720 },
    { width: 1366, height: 768 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport)
    await page.goto('/')
    await expect(page.locator('tbody tr')).toHaveCount(
      Math.min(pageSize, total),
    )
    for (let currentPage = 1; currentPage <= totalPages; currentPage++) {
      if (currentPage > 1) {
        await page.getByRole('button', { name: 'Next page' }).click()
        await expect(
          page.getByText(pageRange(currentPage, pageSize, total)),
        ).toBeVisible()
      }
      const dimensions = await page.evaluate(() => ({
        width: document.documentElement.scrollWidth,
        height: document.documentElement.scrollHeight,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
      }))
      expect(dimensions.width).toBeLessThanOrEqual(dimensions.viewportWidth)
      expect(dimensions.height).toBeLessThanOrEqual(dimensions.viewportHeight)
      if (viewport.width === 1920) {
        const layout = await page.locator('.app-layout').boundingBox()
        expect(layout).not.toBeNull()
        expect(layout!.width).toBeGreaterThan(viewport.width * 0.94)
        for (const panel of [
          page.getByRole('form', { name: 'Search filters' }),
          page.getByRole('region', { name: 'Results' }),
        ]) {
          const bounds = await panel.boundingBox()
          expect(bounds).not.toBeNull()
          expect(bounds!.y + bounds!.height).toBeGreaterThan(
            viewport.height - 32,
          )
        }
      }
      await page.screenshot({
        path: testInfo.outputPath(`${viewport.width}-page-${currentPage}.png`),
        fullPage: true,
      })
    }
  }
})

test('real API: pagination, ranking, combined filters, validation, and no results', async ({
  page,
  request,
}, testInfo) => {
  const { pageSize, total, totalPages } = await getMetadata(request)
  await page.goto('/')
  await expect(page.locator('tbody tr')).toHaveCount(Math.min(pageSize, total))
  await expect(page.getByText('12 listings', { exact: true })).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Previous page' }),
  ).toBeDisabled()
  await page.screenshot({
    path: testInfo.outputPath('desktop.png'),
    fullPage: true,
  })
  const firstPageIdentities = await page.locator('.source').allTextContents()
  await page.getByRole('button', { name: `Go to page ${totalPages}` }).click()
  await expect(
    page.getByText(pageRange(totalPages, pageSize, total)),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
  const lastPageIdentities = await page.locator('.source').allTextContents()
  expect(
    lastPageIdentities.filter((identity) =>
      firstPageIdentities.includes(identity),
    ),
  ).toEqual([])

  await page.getByLabel('Target budget', { exact: true }).fill('450000')
  await page.getByRole('button', { name: 'Search listings' }).click()
  await expect(page.getByText(pageRange(1, pageSize, total))).toBeVisible()
  await expect(page.locator('tbody tr').first()).toHaveAccessibleName(
    '123 Main St, Apt 4B',
  )

  await page.getByLabel('City', { exact: true }).fill(' springfield ')
  await page.getByLabel('Description keyword').fill('FENCED')
  await page.getByLabel('Min. price').fill('525000')
  await page.getByLabel('Max. price').fill('527500')
  await page.getByLabel('Minimum bedrooms').fill('3')
  await page.getByRole('button', { name: 'Search listings' }).click()
  await expect(page.locator('tbody tr')).toHaveCount(2)
  await expect(page.locator('tbody tr').first()).toHaveAccessibleName(
    '456 Oak Ave',
  )

  await page.getByLabel('Max. price').fill('400000')
  await page.getByRole('button', { name: 'Search listings' }).click()
  await expect(page.getByRole('alert')).toContainText('Please check')
  await expect(page.getByLabel('Max. price')).toBeFocused()

  await page.getByRole('button', { name: 'Reset filters' }).click()
  await expect(page.locator('tbody tr')).toHaveCount(Math.min(pageSize, total))
  await page.getByLabel('City', { exact: true }).fill('Atlantis')
  await page.getByRole('button', { name: 'Search listings' }).click()
  await expect(page.getByText('No listings match your search')).toBeVisible()
  await expect(page.locator('tbody tr')).toHaveCount(0)
  await page.getByRole('button', { name: 'Clear filters' }).click()
  await expect(page.locator('tbody tr')).toHaveCount(Math.min(pageSize, total))
})

test('mobile layout fits without horizontal scrolling', async ({
  page,
  request,
}, testInfo) => {
  const { pageSize, total } = await getMetadata(request)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.locator('tbody tr')).toHaveCount(Math.min(pageSize, total))
  await page.screenshot({
    path: testInfo.outputPath('mobile.png'),
    fullPage: true,
  })
  const fits = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  )
  expect(fits).toBe(true)
  await page.getByLabel('City', { exact: true }).fill('Reston')
  await page.getByRole('button', { name: 'Search listings' }).click()
  await expect(page.locator('tbody tr')).toHaveCount(2)
})

test('partial result pages keep the table height and pagination position stable', async ({
  page,
  request,
}, testInfo) => {
  const filteredResponse = await request.get('/api/listings', {
    params: { minPrice: 399500 },
  })
  expect(filteredResponse.ok()).toBe(true)
  const filtered: SearchResponse = await filteredResponse.json()
  const lastPageCount = filtered.total % filtered.pageSize
  expect(lastPageCount).toBeGreaterThan(0)

  for (const viewport of [
    { width: 1280, height: 720 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport)
    await page.goto('/')
    const table = page.getByRole('table', { name: 'Listing results' })
    await expect(table).toBeVisible()
    const initialTable = await table.boundingBox()
    const initialPagination = await page
      .locator('.pagination-row')
      .boundingBox()
    const initialPanel = await page
      .getByRole('region', { name: 'Results' })
      .boundingBox()
    expect(initialTable).not.toBeNull()
    expect(initialPagination).not.toBeNull()
    expect(initialPanel).not.toBeNull()

    async function expectStableLayout() {
      const bounds = await table.boundingBox()
      const pagination = await page.locator('.pagination-row').boundingBox()
      expect(bounds).not.toBeNull()
      expect(pagination).not.toBeNull()
      expect(
        Math.abs(bounds!.height - initialTable!.height),
      ).toBeLessThanOrEqual(2)
      expect(
        Math.abs(pagination!.y - initialPagination!.y),
      ).toBeLessThanOrEqual(2)
      expect(
        await page.evaluate(() => document.documentElement.scrollHeight),
      ).toBeLessThanOrEqual(viewport.height)
    }

    await page.getByLabel('City', { exact: true }).fill('Reston')
    await page.getByRole('button', { name: 'Search listings' }).click()
    await expect(page.getByText('2 listings', { exact: true })).toBeVisible()
    await expect(page.locator('tbody tr')).toHaveCount(2)
    await expectStableLayout()

    await page.getByLabel('City', { exact: true }).fill('')
    await page.getByLabel('Min. price').fill('470000')
    await page.getByLabel('Max. price').fill('470000')
    await page.getByRole('button', { name: 'Search listings' }).click()
    await expect(page.getByText('1 listing', { exact: true })).toBeVisible()
    await expect(page.locator('tbody tr')).toHaveCount(1)
    await expectStableLayout()

    await page.getByLabel('Min. price').fill('399500')
    await page.getByLabel('Max. price').fill('')
    await page.getByRole('button', { name: 'Search listings' }).click()
    await expect(
      page.getByText(`${filtered.total} listings`, { exact: true }),
    ).toBeVisible()
    await page
      .getByRole('button', { name: `Go to page ${filtered.totalPages}` })
      .click()
    await expect(
      page.getByText(
        pageRange(filtered.totalPages, filtered.pageSize, filtered.total),
      ),
    ).toBeVisible()
    await expect(page.locator('tbody tr')).toHaveCount(lastPageCount)
    await expectStableLayout()
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.width}-partial-page.png`),
      fullPage: true,
    })

    await page.getByLabel('City', { exact: true }).fill('Atlantis')
    await page.getByRole('button', { name: 'Search listings' }).click()
    await expect(page.getByText('No listings match your search')).toBeVisible()
    const emptyPanel = await page
      .getByRole('region', { name: 'Results' })
      .boundingBox()
    expect(emptyPanel).not.toBeNull()
    expect(
      Math.abs(emptyPanel!.height - initialPanel!.height),
    ).toBeLessThanOrEqual(2)
  }
})

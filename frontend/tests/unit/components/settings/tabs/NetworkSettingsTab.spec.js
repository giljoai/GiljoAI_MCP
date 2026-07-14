/**
 * Test suite for NetworkSettingsTab.vue component
 *
 * FE-6239: Network settings UX simplification (follow-on to INF-6236).
 * - Read-only Host IP / Port rows (real responding address, not config external_host)
 * - HTTPS section: toggle gated until a cert is provisioned; bring-your-own-cert
 *   upload + reference-by-path; cert-obtain guide + rootCA trust walls moved to the
 *   user guide (single link); CORS section + Save button removed.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import NetworkSettingsTab from '@/components/settings/tabs/NetworkSettingsTab.vue'

describe('NetworkSettingsTab.vue', () => {
  let vuetify
  let wrapper

  const RouterLinkStub = { props: ['to'], template: '<a><slot /></a>' }

  const mountTab = (props = {}) =>
    mount(NetworkSettingsTab, {
      props: {
        serverHostDisplay: '192.0.2.100',
        serverPort: 7272,
        sslEnabled: false,
        loading: false,
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
    // SSL status is loaded on mount via fetch; stub it so tests are deterministic.
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ssl_enabled: false, has_certificate: false, cert_path: null }),
    })
  })

  afterEach(() => {
    if (wrapper) wrapper.unmount()
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders with the new props', () => {
      wrapper = mountTab()
      expect(wrapper.exists()).toBe(true)
    })

    it('displays title "Network Configuration"', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Network Configuration')
    })

    it('uses the simplified "Server Configuration" heading (no "from Installation")', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Server Configuration')
      expect(wrapper.text()).not.toContain('Server Configuration from Installation')
    })

    it('keeps the installation/config.yaml explanatory note', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Network settings are configured during installation')
      expect(wrapper.text()).toContain('config.yaml')
    })
  })

  describe('Server info rows (read-only Host IP / Port)', () => {
    it('renders Host IP and Port as read-only rows, not editable fields', async () => {
      wrapper = mountTab({ serverHostDisplay: '192.0.2.100', serverPort: 7272 })
      await wrapper.vm.$nextTick()

      const host = wrapper.find('[data-test="server-host"]')
      const port = wrapper.find('[data-test="server-port"]')
      expect(host.exists()).toBe(true)
      expect(port.exists()).toBe(true)
      expect(host.text()).toBe('192.0.2.100')
      expect(port.text()).toBe('7272')

      // The old editable-looking text fields are gone.
      expect(wrapper.find('[data-test="external-host-field"]').exists()).toBe(false)
      expect(wrapper.find('[data-test="api-port-field"]').exists()).toBe(false)
      expect(wrapper.find('[data-test="frontend-port-field"]').exists()).toBe(false)
    })

    it('shows multiple host IPs verbatim when the server answers on several', async () => {
      wrapper = mountTab({ serverHostDisplay: '192.0.2.100, 198.51.100.5' })
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="server-host"]').text()).toBe('192.0.2.100, 198.51.100.5')
    })

    it('hides server info while loading', async () => {
      wrapper = mountTab({ loading: true })
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="server-info"]').exists()).toBe(false)
    })
  })

  describe('HTTPS section', () => {
    it('renders the HTTPS status section', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="https-status-section"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('HTTPS')
    })

    it('gates the toggle (disabled + hint) until a certificate is provisioned', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      // Loaded SSL status has no certificate -> hint visible, toggle disabled.
      expect(wrapper.find('[data-test="ssl-needs-cert-hint"]').exists()).toBe(true)
      const toggle = wrapper.find('[data-test="ssl-toggle"]')
      expect(toggle.exists()).toBe(true)
      expect(toggle.attributes('disabled')).toBeDefined()
    })
  })

  describe('Bring-your-own-cert provisioning', () => {
    it('renders the cert provisioning section with upload + path options', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cert-provision-section"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="cert-upload-btn"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="cert-ref-btn"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('GiljoAI does not create certificates')
    })

    it('errors when uploading without both files (no silent no-op)', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      await wrapper.find('[data-test="cert-upload-btn"]').trigger('click')
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Select both a certificate')
    })

    it('errors when referencing without both paths', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      await wrapper.find('[data-test="cert-ref-btn"]').trigger('click')
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Enter both the certificate path and the key path')
    })
  })

  describe('Removed surfaces (moved to the user guide / dropped)', () => {
    it('no longer renders the cert-obtain accordion (mkcert/Let\'s Encrypt how-to)', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="https-setup-toggle"]').exists()).toBe(false)
      expect(wrapper.text()).not.toContain('How to set up trusted HTTPS certificates')
    })

    it('no longer renders the "Connect Another Machine" rootCA wall', async () => {
      wrapper = mountTab({ sslEnabled: true })
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).not.toContain('Connect Another Machine')
      expect(wrapper.text()).not.toContain('rootCA.pem')
    })

    it('no longer renders the CORS section', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cors-origins-section"]').exists()).toBe(false)
      expect(wrapper.text()).not.toContain('CORS Allowed Origins')
    })

    it('no longer renders the dead Save Changes button', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="save-button"]').exists()).toBe(false)
    })

    it('links to the user guide for obtaining/trusting a certificate', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      const link = wrapper.find('[data-test="https-guide-link"]')
      expect(link.exists()).toBe(true)
      expect(link.text()).toContain('guide')
    })

    it('no longer shows the AI coding agent note (moved to the user guide)', async () => {
      wrapper = mountTab({ sslEnabled: true })
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).not.toContain('AI coding agent note')
    })
  })

  describe('Provide-a-certificate section', () => {
    it('renders Option A / Option B as collapsible panels (not a nested frame)', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cert-provision-panels"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="cert-upload-panel"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="cert-ref-panel"]').exists()).toBe(true)
    })
  })

  describe('Certificate status in the HTTPS banner', () => {
    it('shows expiry + covered hostnames when a certificate is present', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ssl_enabled: true,
            has_certificate: true,
            cert_path: '/etc/giljo/certs/server.pem',
            cert_not_after: '2027-03-01',
            cert_sans: ['192.0.2.10', 'localhost'],
            cert_expired: false,
          }),
      })
      wrapper = mountTab({ sslEnabled: true })
      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 0))
      await wrapper.vm.$nextTick()

      const status = wrapper.find('[data-test="cert-status"]')
      expect(status.exists()).toBe(true)
      expect(status.text()).toContain('2027-03-01')
      expect(status.text()).toContain('localhost')
      // the raw path is no longer shown as a standalone line; it lives in the title tooltip
      expect(status.attributes('title')).toBe('/etc/giljo/certs/server.pem')
    })
  })

  describe('Reload button', () => {
    it('has a Reload button that emits refresh', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      const reloadButton = wrapper.find('[data-test="reload-button"]')
      expect(reloadButton.exists()).toBe(true)
      expect(reloadButton.text()).toContain('Reload')

      await reloadButton.trigger('click')
      expect(wrapper.emitted('refresh')).toBeTruthy()
      expect(wrapper.emitted('refresh').length).toBe(1)
    })

    it('Reload button also emits reload-domains (FE-6245)', async () => {
      wrapper = mountTab()
      await wrapper.vm.$nextTick()
      const reloadButton = wrapper.find('[data-test="reload-button"]')
      await reloadButton.trigger('click')
      expect(wrapper.emitted('reload-domains')).toBeTruthy()
    })
  })

  // FE-6245: Cookie Domain Whitelist moved from Security tab to Network tab
  describe('Cookie Domain Whitelist', () => {
    const mountWithDomains = (cookieDomains = [], extra = {}) =>
      mountTab({ cookieDomains, ...extra })

    it('renders the cookie whitelist section', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cookie-whitelist-section"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('Cookie Domain Whitelist')
    })

    it('shows empty state when no domains are configured', async () => {
      wrapper = mountWithDomains([])
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cookie-empty-state"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('No domain names configured')
    })

    it('renders the add-domain input', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cookie-new-domain-input"]').exists()).toBe(true)
    })

    it('emits add-domain with the trimmed value on addCookieDomain call', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      wrapper.vm.newCookieDomain = 'new.example.com'
      await wrapper.vm.$nextTick()
      wrapper.vm.addCookieDomain()
      await wrapper.vm.$nextTick()
      expect(wrapper.emitted('add-domain')).toBeTruthy()
      expect(wrapper.emitted('add-domain')[0]).toEqual(['new.example.com'])
    })

    it('clears the input after a successful add', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      wrapper.vm.newCookieDomain = 'new.example.com'
      wrapper.vm.addCookieDomain()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.newCookieDomain).toBe('')
    })

    it('does not emit add-domain for an empty input', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      wrapper.vm.addCookieDomain()
      expect(wrapper.emitted('add-domain')).toBeFalsy()
    })

    it('emits remove-domain when removeCookieDomain is called', async () => {
      wrapper = mountWithDomains(['app.example.com'])
      await wrapper.vm.$nextTick()
      wrapper.vm.removeCookieDomain('app.example.com')
      await wrapper.vm.$nextTick()
      expect(wrapper.emitted('remove-domain')).toBeTruthy()
      expect(wrapper.emitted('remove-domain')[0]).toEqual(['app.example.com'])
    })

    it('rejects IP address input and sets cookieDomainError', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      wrapper.vm.newCookieDomain = '192.0.2.1'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.cookieDomainError).toContain('IP addresses are not allowed')
    })

    it('rejects invalid domain format', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      wrapper.vm.newCookieDomain = 'invalid..domain'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.cookieDomainError).toContain('Invalid domain format')
    })

    it('accepts valid domain names', async () => {
      wrapper = mountWithDomains()
      await wrapper.vm.$nextTick()
      wrapper.vm.newCookieDomain = 'valid.example.com'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.cookieDomainError).toBe('')
    })

    it('does not emit add-domain for a duplicate domain', async () => {
      wrapper = mountWithDomains(['app.example.com'])
      await wrapper.vm.$nextTick()
      wrapper.vm.newCookieDomain = 'app.example.com'
      // Flush the pending watch so it fires and clears prior errors first;
      // then addCookieDomain runs and sets the duplicate error without the
      // watch overwriting it on the SAME tick.
      await wrapper.vm.$nextTick()
      wrapper.vm.addCookieDomain()
      // Assert synchronously before the next tick (newCookieDomain was not
      // changed during addCookieDomain, so the watch does not re-fire).
      expect(wrapper.emitted('add-domain')).toBeFalsy()
      expect(wrapper.vm.cookieDomainError).toContain('already')
    })

    it('shows loading indicator when cookieLoading is true', async () => {
      wrapper = mountWithDomains([], { cookieLoading: true })
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cookie-loading-indicator"]').exists()).toBe(true)
    })

    it('renders the cookie feedback alert when cookieFeedback is set', async () => {
      wrapper = mountTab({
        cookieDomains: [],
        cookieFeedback: { type: 'success', message: 'Domain added.' },
      })
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-test="cookie-feedback-alert"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('Domain added.')
    })
  })
})

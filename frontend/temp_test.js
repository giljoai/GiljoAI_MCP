import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import JobReadAckIndicators from 'frontend/src/components/StatusBoard/JobReadAckIndicators.vue'

const vuetify = createVuetify({
  components,
  directives,
})

const wrapper = mount(JobReadAckIndicators, {
  props: {
    missionReadAt: null,
    missionAcknowledgedAt: null,
  },
  global: {
    plugins: [vuetify],
  },
})

console.log('Component HTML:', wrapper.html())
console.log('All icons:', wrapper.findAll('i').length)
console.log('Read wrapper HTML:', wrapper.find('.read-indicator').html())

<template>
  <v-card class="git-settings" elevation="2">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/code.svg" width="24" height="24" alt="Git" />
      </v-icon>
      <span>Git Integration Settings</span>
      <v-spacer />
      <v-btn
        v-if="gitConfig && gitConfig.is_configured"
        color="success"
        prepend-icon="mdi-check"
        variant="text"
        size="small"
      >
        Configured
      </v-btn>
      <v-btn v-else color="warning" prepend-icon="mdi-alert" variant="text" size="small">
        Not Configured
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Git Status Overview -->
      <v-alert v-if="gitStatus && !gitStatus.repo_exists" type="info" variant="tonal" class="mb-4">
        <v-alert-title>Repository Not Initialized</v-alert-title>
        <div>Git repository not found. Initialize one to enable version control.</div>
      </v-alert>

      <v-alert
        v-if="gitConfig && gitConfig.last_error"
        type="error"
        variant="tonal"
        class="mb-4"
        closable
        @click:close="clearError"
      >
        <v-alert-title>Git Error</v-alert-title>
        <div>{{ gitConfig.last_error }}</div>
      </v-alert>

      <!-- Configuration Form -->
      <v-form ref="configForm" v-model="formValid" @submit.prevent="saveConfiguration">
        <v-row>
          <!-- Repository Configuration -->
          <v-col cols="12">
            <v-text-field
              v-model="form.repo_url"
              label="Repository URL"
              placeholder="https://github.com/username/repo.git"
              prepend-icon="mdi-git"
              :rules="[rules.required, rules.url]"
              hide-details="auto"
              class="mb-2"
            />
          </v-col>

          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.branch"
              label="Default Branch"
              placeholder="main"
              prepend-icon="mdi-source-branch"
              :rules="[rules.required]"
              hide-details="auto"
              class="mb-2"
            />
          </v-col>

          <v-col cols="12" md="6">
            <v-select
              v-model="form.auth_method"
              :items="authMethods"
              label="Authentication Method"
              prepend-icon="mdi-shield-key"
              :rules="[rules.required]"
              hide-details="auto"
              class="mb-2"
            />
          </v-col>

          <!-- Authentication Fields -->
          <template v-if="form.auth_method === 'system'">
            <v-col cols="12">
              <v-alert type="success" variant="tonal" class="mb-2">
                <v-alert-title>Using System Authentication</v-alert-title>
                <div>
                  Using existing git configuration and credential helpers from your system. This
                  leverages GitHub Desktop, SSH keys, or other authentication already set up.
                </div>
              </v-alert>
            </v-col>
          </template>

          <template v-if="form.auth_method === 'https'">
            <v-col cols="12" md="6">
              <v-text-field
                v-model="form.username"
                label="Username"
                prepend-icon="mdi-account"
                :rules="[rules.required]"
                hide-details="auto"
                class="mb-2"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="form.password"
                label="Password / Personal Access Token"
                type="password"
                prepend-icon="mdi-lock"
                :rules="[rules.required]"
                hide-details="auto"
                class="mb-2"
              />
            </v-col>
          </template>

          <template v-if="form.auth_method === 'ssh'">
            <v-col cols="12">
              <v-text-field
                v-model="form.ssh_key_path"
                label="SSH Private Key Path"
                placeholder="/path/to/private/key"
                prepend-icon="mdi-key"
                :rules="[rules.required]"
                hide-details="auto"
                class="mb-2"
              />
              <v-alert type="info" variant="tonal" class="mt-2">
                <div class="text-caption">
                  Ensure your SSH key is configured and accessible to the server.
                </div>
              </v-alert>
            </v-col>
          </template>

          <template v-if="form.auth_method === 'token'">
            <v-col cols="12">
              <v-text-field
                v-model="form.password"
                label="Personal Access Token"
                type="password"
                prepend-icon="mdi-key-variant"
                :rules="[rules.required]"
                hide-details="auto"
                class="mb-2"
              />
              <v-alert type="info" variant="tonal" class="mt-2">
                <div class="text-caption">
                  Use a personal access token with appropriate repository permissions.
                </div>
              </v-alert>
            </v-col>
          </template>

          <!-- Automation Settings -->
          <v-col cols="12">
            <v-divider class="my-4" />
            <h3 class="text-h6 mb-3">Automation Settings</h3>
          </v-col>

          <v-col cols="12" md="6">
            <v-switch
              v-model="form.auto_commit"
              label="Auto-commit on project completion"
              color="primary"
              hide-details
            />
          </v-col>

          <v-col cols="12" md="6">
            <v-switch
              v-model="form.auto_push"
              label="Auto-push after commits"
              color="primary"
              hide-details
            />
          </v-col>

          <v-col cols="12">
            <v-textarea
              v-model="form.commit_message_template"
              label="Commit Message Template (Optional)"
              placeholder="Leave empty for auto-generated messages"
              rows="3"
              prepend-icon="mdi-message-text"
              hide-details="auto"
              class="mb-2"
            />
          </v-col>

          <!-- Webhook Configuration -->
          <v-col cols="12">
            <v-divider class="my-4" />
            <h3 class="text-h6 mb-3">CI/CD Integration</h3>
          </v-col>

          <v-col cols="12" md="8">
            <v-text-field
              v-model="form.webhook_url"
              label="Webhook URL (Optional)"
              placeholder="https://your-ci-system.com/webhook"
              prepend-icon="mdi-webhook"
              :rules="[rules.webhookUrl]"
              hide-details="auto"
              class="mb-2"
            />
          </v-col>

          <v-col cols="12" md="4">
            <v-text-field
              v-model="form.webhook_secret"
              label="Webhook Secret"
              type="password"
              prepend-icon="mdi-shield-lock"
              :disabled="!form.webhook_url"
              hide-details="auto"
              class="mb-2"
            />
          </v-col>
        </v-row>

        <!-- Action Buttons -->
        <v-row class="mt-4">
          <v-col cols="12" class="d-flex gap-2">
            <v-btn
              type="submit"
              color="primary"
              prepend-icon="mdi-content-save"
              :loading="saving"
              :disabled="!formValid"
            >
              Save Configuration
            </v-btn>

            <v-btn
              v-if="!gitStatus?.repo_exists"
              color="success"
              prepend-icon="mdi-source-repository"
              :loading="initializing"
              :disabled="!gitConfig?.is_configured"
              @click="initializeRepository"
            >
              Initialize Repository
            </v-btn>

            <v-btn
              v-if="gitStatus?.repo_exists"
              color="info"
              prepend-icon="mdi-refresh"
              :loading="refreshing"
              @click="refreshStatus"
            >
              Refresh Status
            </v-btn>

            <v-btn
              color="secondary"
              prepend-icon="mdi-test-tube"
              :loading="testing"
              :disabled="!gitConfig?.is_configured"
              @click="testConnection"
            >
              Test Connection
            </v-btn>
          </v-col>
        </v-row>
      </v-form>

      <!-- Current Status -->
      <v-divider class="my-6" />
      <h3 class="text-h6 mb-3">Current Status</h3>

      <v-row v-if="gitStatus">
        <v-col cols="12" md="6">
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Repository Status</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  :color="gitStatus.repo_exists ? 'success' : 'warning'"
                  size="small"
                  variant="tonal"
                >
                  {{ gitStatus.repo_exists ? 'Initialized' : 'Not Initialized' }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="gitStatus.status">
              <v-list-item-title>Current Branch</v-list-item-title>
              <v-list-item-subtitle>{{
                gitStatus.status.current_branch || 'Unknown'
              }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="gitStatus.status">
              <v-list-item-title>Pending Changes</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  :color="gitStatus.status.has_changes ? 'warning' : 'success'"
                  size="small"
                  variant="tonal"
                >
                  {{ gitStatus.status.changed_files || 0 }} files
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-col>

        <v-col cols="12" md="6">
          <v-list density="compact">
            <v-list-item v-if="gitConfig">
              <v-list-item-title>Last Commit</v-list-item-title>
              <v-list-item-subtitle>{{
                gitConfig.last_commit_hash || 'None'
              }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="gitConfig">
              <v-list-item-title>Last Push</v-list-item-title>
              <v-list-item-subtitle>
                {{ gitConfig.last_push_at ? formatDate(gitConfig.last_push_at) : 'Never' }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="gitConfig">
              <v-list-item-title>Webhook Status</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  :color="gitConfig.webhook_configured ? 'success' : 'default'"
                  size="small"
                  variant="tonal"
                >
                  {{ gitConfig.webhook_configured ? 'Configured' : 'Not Configured' }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { api } from '@/services/api'

export default {
  name: 'GitSettings',
  props: {
    productId: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const { showToast } = useToast()

    // Reactive data
    const formValid = ref(false)
    const configForm = ref(null)
    const saving = ref(false)
    const initializing = ref(false)
    const refreshing = ref(false)
    const testing = ref(false)

    const gitConfig = ref(null)
    const gitStatus = ref(null)

    // Form data
    const form = reactive({
      repo_url: '',
      branch: 'main',
      auth_method: 'system',
      username: '',
      password: '',
      ssh_key_path: '',
      auto_commit: true,
      auto_push: false,
      commit_message_template: '',
      webhook_url: '',
      webhook_secret: '',
    })

    // Static data
    const authMethods = [
      { title: 'System Authentication (Recommended)', value: 'system' },
      { title: 'HTTPS (Username/Password)', value: 'https' },
      { title: 'SSH Key', value: 'ssh' },
      { title: 'Personal Access Token', value: 'token' },
    ]

    // Validation rules
    const rules = {
      required: (value) => !!value || 'This field is required',
      url: (value) => {
        if (!value) return true
        const urlPattern = /^(https?|git)(:\/\/|@)([^\s/$.?#].[^\s]*)/i
        return urlPattern.test(value) || 'Please enter a valid repository URL'
      },
      webhookUrl: (value) => {
        if (!value) return true
        const urlPattern = /^https?:\/\/[^\s/$.?#].[^\s]*$/i
        return urlPattern.test(value) || 'Please enter a valid webhook URL'
      },
    }

    // Methods
    const loadGitConfig = async () => {
      try {
        const response = await api.get(`/git/status/${props.productId}`)
        if (response.data.success) {
          gitStatus.value = response.data
          gitConfig.value = response.data.config

          if (gitConfig.value) {
            // Populate form with existing config
            Object.assign(form, {
              repo_url: gitConfig.value.repo_url || '',
              branch: gitConfig.value.branch || 'main',
              auth_method: gitConfig.value.auth_method || 'system',
              username: gitConfig.value.username || '',
              auto_commit: gitConfig.value.auto_commit ?? true,
              auto_push: gitConfig.value.auto_push ?? false,
              commit_message_template: gitConfig.value.commit_message_template || '',
              webhook_url: gitConfig.value.webhook_url || '',
              // Don't populate passwords for security
              password: '',
              ssh_key_path: gitConfig.value.ssh_key_path || '',
            })
          }
        }
      } catch (error) {
        console.error('Failed to load git configuration:', error)
        showToast('Failed to load git configuration', 'error')
      }
    }

    const saveConfiguration = async () => {
      if (!formValid.value) return

      saving.value = true
      try {
        const response = await api.post('/git/configure', {
          product_id: props.productId,
          ...form,
        })

        if (response.data.success) {
          showToast('Git configuration saved successfully', 'success')
          await loadGitConfig() // Reload to get updated status
        } else {
          throw new Error(response.data.error || 'Configuration failed')
        }
      } catch (error) {
        console.error('Failed to save git configuration:', error)
        showToast(`Failed to save configuration: ${error.message}`, 'error')
      } finally {
        saving.value = false
      }
    }

    const initializeRepository = async () => {
      initializing.value = true
      try {
        const response = await api.post('/git/init', {
          product_id: props.productId,
          repo_path: process.env.VUE_APP_PROJECT_ROOT || '/app',
          initial_commit: true,
        })

        if (response.data.success) {
          showToast('Repository initialized successfully', 'success')
          await loadGitConfig()
        } else {
          throw new Error(response.data.error || 'Initialization failed')
        }
      } catch (error) {
        console.error('Failed to initialize repository:', error)
        showToast(`Failed to initialize repository: ${error.message}`, 'error')
      } finally {
        initializing.value = false
      }
    }

    const refreshStatus = async () => {
      refreshing.value = true
      try {
        await loadGitConfig()
        showToast('Status refreshed', 'info')
      } catch (error) {
        showToast('Failed to refresh status', 'error')
      } finally {
        refreshing.value = false
      }
    }

    const testConnection = async () => {
      testing.value = true
      try {
        // This would test git connectivity
        const response = await api.post('/git/test', {
          product_id: props.productId,
        })

        if (response.data.success) {
          showToast('Git connection test successful', 'success')
        } else {
          throw new Error(response.data.error || 'Connection test failed')
        }
      } catch (error) {
        console.error('Git connection test failed:', error)
        showToast(`Connection test failed: ${error.message}`, 'error')
      } finally {
        testing.value = false
      }
    }

    const clearError = async () => {
      try {
        await api.post('/git/clear-error', {
          product_id: props.productId,
        })
        await loadGitConfig()
      } catch (error) {
        console.error('Failed to clear error:', error)
      }
    }

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleString()
    }

    // Watchers
    watch(() => props.productId, loadGitConfig, { immediate: true })

    // Lifecycle
    onMounted(() => {
      loadGitConfig()
    })

    return {
      // Reactive data
      formValid,
      configForm,
      saving,
      initializing,
      refreshing,
      testing,
      gitConfig,
      gitStatus,
      form,

      // Static data
      authMethods,
      rules,

      // Methods
      saveConfiguration,
      initializeRepository,
      refreshStatus,
      testConnection,
      clearError,
      formatDate,
    }
  },
}
</script>

<style scoped>
.git-settings {
  max-width: 100%;
}

.v-alert {
  margin-bottom: 16px;
}

.v-divider {
  margin: 24px 0;
}

.d-flex.gap-2 > * + * {
  margin-left: 8px;
}
</style>

# Common Components

Reusable UI components for consistent application styling.

## BaseDialog

Standardized dialog component for confirmations, warnings, and forms.

### Types

| Type | Color | Icon | Use Case |
|------|-------|------|----------|
| `info` | Blue | mdi-information | Informational, no risk |
| `warning` | Amber | mdi-alert | Caution, reversible action |
| `danger` | Red | mdi-alert-circle | Destructive, irreversible actions |
| `success` | Green | mdi-check-circle | Positive confirmation |

### Sizes

| Size | Width | Use Case |
|------|-------|----------|
| `sm` | 400px | Simple alerts |
| `md` | 500px | Standard confirmations (default) |
| `lg` | 650px | Detailed warnings with context |
| `xl` | 800px | Forms, complex content |

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `v-model` | Boolean | required | Dialog open state |
| `type` | String | 'info' | Dialog type (info/warning/danger/success) |
| `title` | String | required | Dialog title |
| `message` | String | '' | Simple message (or use default slot) |
| `confirmLabel` | String | 'Confirm' | Confirm button text |
| `cancelText` | String | 'Cancel' | Cancel button text |
| `size` | String/Number | 'md' | Dialog width (sm/md/lg/xl or pixels) |
| `persistent` | Boolean | true | Prevent closing by clicking outside |
| `loading` | Boolean | false | Show loading state on confirm button |
| `confirmText` | String | '' | Text user must type to confirm |
| `confirmCheckbox` | Boolean | false | Require checkbox confirmation |
| `confirmCheckboxLabel` | String | 'I understand...' | Checkbox label |
| `hideIcon` | Boolean | false | Hide title bar icon |
| `icon` | String | '' | Custom icon (overrides type default) |

### Events

| Event | Payload | Description |
|-------|---------|-------------|
| `confirm` | none | User confirmed the action |
| `cancel` | none | User cancelled or closed dialog |

### Slots

| Slot | Description |
|------|-------------|
| `default` | Main content area |
| `titleAppend` | Content after title (e.g., chips, badges) |
| `actions` | Override default action buttons |

### Examples

#### Simple Warning
```vue
<BaseDialog
  v-model="showDialog"
  type="warning"
  title="Switch Product?"
  message="This will change the active context for all new operations."
  confirm-label="Switch"
  @confirm="handleSwitch"
/>
```

#### Danger with Text Confirmation
```vue
<BaseDialog
  v-model="showDeleteDialog"
  type="danger"
  title="Delete Item?"
  confirm-text="DELETE"
  confirm-label="Delete Permanently"
  :loading="isDeleting"
  @confirm="handleDelete"
>
  <v-alert type="warning" variant="tonal" class="mb-4">
    This action cannot be undone.
  </v-alert>
  <p>Are you sure you want to delete <strong>{{ item.name }}</strong>?</p>
</BaseDialog>
```

#### Info with Checkbox Confirmation
```vue
<BaseDialog
  v-model="showMigrationDialog"
  type="info"
  title="Run Migration"
  confirm-checkbox
  confirm-checkbox-label="I have backed up my database"
  @confirm="runMigration"
>
  <p>This will update the database schema.</p>
</BaseDialog>
```

#### Custom Actions
```vue
<BaseDialog
  v-model="showDialog"
  type="info"
  title="Choose Action"
>
  <p>What would you like to do?</p>

  <template #actions>
    <v-btn variant="text" @click="showDialog = false">Cancel</v-btn>
    <v-btn color="primary" @click="handleOptionA">Option A</v-btn>
    <v-btn color="secondary" @click="handleOptionB">Option B</v-btn>
  </template>
</BaseDialog>
```

### Migration Guide

To migrate an existing dialog to BaseDialog:

1. Replace `<v-dialog>` with `<BaseDialog>`
2. Move title text to `title` prop
3. Remove `<v-card>`, `<v-card-title>`, `<v-card-actions>` wrappers
4. Move content into default slot
5. Add `type` prop based on dialog purpose
6. Add `@confirm` and `@cancel` handlers
7. Remove manual confirmation state (BaseDialog handles it)

**Before:**
```vue
<v-dialog v-model="show" max-width="500">
  <v-card>
    <v-card-title class="bg-error">
      <v-icon class="mr-2">mdi-alert-circle</v-icon>
      Delete Item?
    </v-card-title>
    <v-card-text>Content here</v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="cancel">Cancel</v-btn>
      <v-btn color="error" @click="confirm">Delete</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**After:**
```vue
<BaseDialog
  v-model="show"
  type="danger"
  title="Delete Item?"
  confirm-label="Delete"
  @confirm="confirm"
  @cancel="cancel"
>
  Content here
</BaseDialog>
```

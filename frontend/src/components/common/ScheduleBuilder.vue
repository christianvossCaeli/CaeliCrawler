<template>
  <div>
    <v-row>
      <v-col cols="12" md="4">
        <v-select
          v-model="mode"
          :items="modeItems"
          :label="t('common.scheduleBuilder.mode')"
          variant="outlined"
          density="compact"
          :disabled="disabled"
        />
      </v-col>

      <v-col cols="12" md="8" v-if="mode === 'interval'">
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="intervalValue"
              type="number"
              min="1"
              :label="t('common.scheduleBuilder.intervalValue')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="intervalUnit"
              :items="unitItems"
              :label="t('common.scheduleBuilder.unit')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="4" v-if="intervalUnit !== 'seconds'">
            <v-select
              v-model="intervalSecond"
              :items="secondItems"
              :label="t('common.scheduleBuilder.time.second')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="4" v-if="intervalUnit === 'hours'">
            <v-select
              v-model="intervalMinute"
              :items="minuteItems"
              :label="t('common.scheduleBuilder.time.minute')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
        </v-row>
      </v-col>

      <v-col cols="12" md="8" v-else-if="mode === 'daily'">
        <v-row>
          <v-col cols="12" md="4">
            <v-select
              v-model="timeHour"
              :items="hourItems"
              :label="t('common.scheduleBuilder.time.hour')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="timeMinute"
              :items="minuteItems"
              :label="t('common.scheduleBuilder.time.minute')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="timeSecond"
              :items="secondItems"
              :label="t('common.scheduleBuilder.time.second')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
        </v-row>
      </v-col>

      <v-col cols="12" md="8" v-else-if="mode === 'weekly'">
        <v-row>
          <v-col cols="12" md="4">
            <v-select
              v-model="dayOfWeek"
              :items="weekdayItems"
              :label="t('common.scheduleBuilder.dayOfWeek')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="8">
            <v-row>
              <v-col cols="12" md="4">
                <v-select
                  v-model="timeHour"
                  :items="hourItems"
                  :label="t('common.scheduleBuilder.time.hour')"
                  variant="outlined"
                  density="compact"
                  :disabled="disabled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="timeMinute"
                  :items="minuteItems"
                  :label="t('common.scheduleBuilder.time.minute')"
                  variant="outlined"
                  density="compact"
                  :disabled="disabled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="timeSecond"
                  :items="secondItems"
                  :label="t('common.scheduleBuilder.time.second')"
                  variant="outlined"
                  density="compact"
                  :disabled="disabled"
                />
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-col>

      <v-col cols="12" md="8" v-else-if="mode === 'monthly'">
        <v-row>
          <v-col cols="12" md="4">
            <v-select
              v-model="dayOfMonth"
              :items="dayOfMonthItems"
              :label="t('common.scheduleBuilder.dayOfMonth')"
              variant="outlined"
              density="compact"
              :disabled="disabled"
            />
          </v-col>
          <v-col cols="12" md="8">
            <v-row>
              <v-col cols="12" md="4">
                <v-select
                  v-model="timeHour"
                  :items="hourItems"
                  :label="t('common.scheduleBuilder.time.hour')"
                  variant="outlined"
                  density="compact"
                  :disabled="disabled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="timeMinute"
                  :items="minuteItems"
                  :label="t('common.scheduleBuilder.time.minute')"
                  variant="outlined"
                  density="compact"
                  :disabled="disabled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="timeSecond"
                  :items="secondItems"
                  :label="t('common.scheduleBuilder.time.second')"
                  variant="outlined"
                  density="compact"
                  :disabled="disabled"
                />
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-col>

      <v-col cols="12" v-else>
        <v-text-field
          v-model="customCron"
          :label="t('common.scheduleBuilder.customLabel')"
          :hint="t('common.scheduleBuilder.customHint')"
          persistent-hint
          variant="outlined"
          density="compact"
          :disabled="disabled"
        />
      </v-col>
    </v-row>

    <div
      v-if="showPreview && previewText"
      class="text-caption text-medium-emphasis mt-2"
    >
      {{ previewText }}
    </div>
    <div
      v-if="timezoneLabel"
      class="text-caption text-medium-emphasis mt-1"
    >
      {{ timezoneLabel }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DEFAULT_SCHEDULE_TIMEZONE, getCronPreview } from '@/utils/cron'

type ScheduleMode = 'interval' | 'daily' | 'weekly' | 'monthly' | 'custom'
type IntervalUnit = 'seconds' | 'minutes' | 'hours'

interface Props {
  modelValue: string
  disabled?: boolean
  showPreview?: boolean
  showAdvanced?: boolean
  scheduleTimezone?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  disabled: false,
  showPreview: true,
  showAdvanced: true,
  scheduleTimezone: DEFAULT_SCHEDULE_TIMEZONE,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { t, locale } = useI18n()

const mode = ref<ScheduleMode>('daily')
const intervalValue = ref(15)
const intervalUnit = ref<IntervalUnit>('minutes')
const intervalMinute = ref(0)
const intervalSecond = ref(0)

const timeHour = ref(6)
const timeMinute = ref(0)
const timeSecond = ref(0)
const dayOfWeek = ref(1)
const dayOfMonth = ref(1)
const customCron = ref('')

const hourItems = computed(() => buildNumberItems(24))
const minuteItems = computed(() => buildNumberItems(60))
const secondItems = computed(() => buildNumberItems(60))
const dayOfMonthItems = computed(() =>
  Array.from({ length: 31 }, (_, index) => ({
    title: String(index + 1),
    value: index + 1,
  }))
)

const weekdayItems = computed(() => {
  const formatter = new Intl.DateTimeFormat(locale.value, { weekday: 'long' })
  const base = new Date(2023, 0, 1)
  const order = [1, 2, 3, 4, 5, 6, 0]
  return order.map((weekday) => {
    const date = new Date(base)
    date.setDate(base.getDate() + weekday)
    return {
      title: formatter.format(date),
      value: weekday,
    }
  })
})

const modeItems = computed(() => {
  const items = [
    { title: t('common.scheduleBuilder.modes.interval'), value: 'interval' },
    { title: t('common.scheduleBuilder.modes.daily'), value: 'daily' },
    { title: t('common.scheduleBuilder.modes.weekly'), value: 'weekly' },
    { title: t('common.scheduleBuilder.modes.monthly'), value: 'monthly' },
  ]

  if (props.showAdvanced) {
    items.push({ title: t('common.scheduleBuilder.modes.custom'), value: 'custom' })
  }

  return items
})

const unitItems = computed(() => [
  { title: t('common.scheduleBuilder.units.seconds'), value: 'seconds' },
  { title: t('common.scheduleBuilder.units.minutes'), value: 'minutes' },
  { title: t('common.scheduleBuilder.units.hours'), value: 'hours' },
])

const previewText = computed(() => {
  if (!props.showPreview || !props.modelValue) return ''

  const preview = getCronPreview(props.modelValue, locale.value, props.scheduleTimezone)
  if (!preview.isValid) {
    return t('common.scheduleBuilder.invalid')
  }

  const parts: string[] = []
  if (preview.description && preview.description !== props.modelValue) {
    parts.push(preview.description)
  }
  if (preview.nextRun) {
    const timezoneSuffix = props.scheduleTimezone ? ` (${props.scheduleTimezone})` : ''
    parts.push(`${t('common.scheduleBuilder.nextRun')}: ${preview.nextRun}${timezoneSuffix}`)
  }

  return parts.length ? parts.join(' - ') : t('common.scheduleBuilder.previewUnavailable')
})

const timezoneLabel = computed(() => {
  if (!props.scheduleTimezone) return ''
  return `${t('common.scheduleBuilder.timezone')}: ${props.scheduleTimezone}`
})

const isSyncing = ref(false)

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      applyDefaults()
      return
    }

    applyParsedState(value)
  },
  { immediate: true }
)

const builtExpression = computed(() => {
  if (mode.value === 'custom') {
    return customCron.value.trim()
  }

  if (mode.value === 'interval') {
    return buildIntervalExpression()
  }

  if (mode.value === 'weekly') {
    return buildWeeklyExpression()
  }

  if (mode.value === 'monthly') {
    return buildMonthlyExpression()
  }

  return buildDailyExpression()
})

watch(builtExpression, (value) => {
  if (isSyncing.value) return
  if (value !== props.modelValue) {
    emit('update:modelValue', value)
  }
})

function buildNumberItems(limit: number): Array<{ title: string; value: number }> {
  return Array.from({ length: limit }, (_, index) => ({
    title: String(index).padStart(2, '0'),
    value: index,
  }))
}

function buildIntervalExpression(): string {
  const interval = Math.max(1, Number(intervalValue.value) || 1)
  if (intervalUnit.value === 'seconds') {
    return `*/${interval} * * * * *`
  }

  if (intervalUnit.value === 'minutes') {
    if (intervalSecond.value > 0) {
      return `${intervalSecond.value} */${interval} * * * *`
    }
    return `*/${interval} * * * *`
  }

  if (intervalSecond.value > 0) {
    return `${intervalSecond.value} ${intervalMinute.value} */${interval} * * *`
  }
  return `${intervalMinute.value} */${interval} * * *`
}

function buildDailyExpression(): string {
  if (timeSecond.value > 0) {
    return `${timeSecond.value} ${timeMinute.value} ${timeHour.value} * * *`
  }
  return `${timeMinute.value} ${timeHour.value} * * *`
}

function buildWeeklyExpression(): string {
  if (timeSecond.value > 0) {
    return `${timeSecond.value} ${timeMinute.value} ${timeHour.value} * * ${dayOfWeek.value}`
  }
  return `${timeMinute.value} ${timeHour.value} * * ${dayOfWeek.value}`
}

function buildMonthlyExpression(): string {
  if (timeSecond.value > 0) {
    return `${timeSecond.value} ${timeMinute.value} ${timeHour.value} ${dayOfMonth.value} * *`
  }
  return `${timeMinute.value} ${timeHour.value} ${dayOfMonth.value} *`
}

function applyDefaults() {
  isSyncing.value = true
  mode.value = 'daily'
  intervalValue.value = 15
  intervalUnit.value = 'minutes'
  intervalMinute.value = 0
  intervalSecond.value = 0
  timeHour.value = 6
  timeMinute.value = 0
  timeSecond.value = 0
  dayOfWeek.value = 1
  dayOfMonth.value = 1
  customCron.value = ''
  nextTick(() => {
    isSyncing.value = false
  })
}

function applyParsedState(expression: string) {
  const parsed = parseCronExpression(expression)
  if (!parsed) {
    if (props.showAdvanced) {
      setCustomExpression(expression)
    } else {
      applyDefaults()
    }
    return
  }

  isSyncing.value = true

  mode.value = parsed.mode
  if (parsed.mode === 'interval') {
    intervalValue.value = parsed.intervalValue
    intervalUnit.value = parsed.intervalUnit
    intervalMinute.value = parsed.intervalMinute
    intervalSecond.value = parsed.intervalSecond
  }

  if (parsed.mode === 'daily') {
    timeHour.value = parsed.timeHour
    timeMinute.value = parsed.timeMinute
    timeSecond.value = parsed.timeSecond
  }

  if (parsed.mode === 'weekly') {
    dayOfWeek.value = parsed.dayOfWeek
    timeHour.value = parsed.timeHour
    timeMinute.value = parsed.timeMinute
    timeSecond.value = parsed.timeSecond
  }

  if (parsed.mode === 'monthly') {
    dayOfMonth.value = parsed.dayOfMonth
    timeHour.value = parsed.timeHour
    timeMinute.value = parsed.timeMinute
    timeSecond.value = parsed.timeSecond
  }

  if (parsed.mode === 'custom') {
    customCron.value = parsed.customExpression
  }

  nextTick(() => {
    isSyncing.value = false
  })
}

function setCustomExpression(expression: string) {
  isSyncing.value = true
  mode.value = 'custom'
  customCron.value = expression
  nextTick(() => {
    isSyncing.value = false
  })
}

function parseCronExpression(expression: string):
  | {
      mode: 'interval'
      intervalValue: number
      intervalUnit: IntervalUnit
      intervalMinute: number
      intervalSecond: number
    }
  | {
      mode: 'daily'
      timeHour: number
      timeMinute: number
      timeSecond: number
    }
  | {
      mode: 'weekly'
      dayOfWeek: number
      timeHour: number
      timeMinute: number
      timeSecond: number
    }
  | {
      mode: 'monthly'
      dayOfMonth: number
      timeHour: number
      timeMinute: number
      timeSecond: number
    }
  | {
      mode: 'custom'
      customExpression: string
    }
  | null {
  const parts = expression.trim().split(/\s+/)
  if (parts.length !== 5 && parts.length !== 6) {
    return null
  }

  const hasSeconds = parts.length === 6
  const [second, minute, hour, dayOfMonth, month, dayOfWeek] = hasSeconds
    ? parts
    : ['0', ...parts]

  const fields = [second, minute, hour, dayOfMonth, month, dayOfWeek]
  if (!fields.every(isSimpleField)) {
    return { mode: 'custom', customExpression: expression }
  }

  const secondStep = parseStep(second)
  const minuteStep = parseStep(minute)
  const hourStep = parseStep(hour)

  const secondNum = parseNumber(second) ?? 0
  const minuteNum = parseNumber(minute)
  const hourNum = parseNumber(hour)
  const dayOfMonthNum = parseNumber(dayOfMonth)
  const dayOfWeekNum = parseNumber(dayOfWeek)

  if (
    secondStep &&
    minute === '*' &&
    hour === '*' &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*'
  ) {
    return {
      mode: 'interval',
      intervalValue: secondStep,
      intervalUnit: 'seconds',
      intervalMinute: 0,
      intervalSecond: 0,
    }
  }

  if (
    minuteStep &&
    hour === '*' &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*'
  ) {
    return {
      mode: 'interval',
      intervalValue: minuteStep,
      intervalUnit: 'minutes',
      intervalMinute: 0,
      intervalSecond: secondNum,
    }
  }

  if (
    hourStep &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*' &&
    minuteNum !== null
  ) {
    return {
      mode: 'interval',
      intervalValue: hourStep,
      intervalUnit: 'hours',
      intervalMinute: minuteNum,
      intervalSecond: secondNum,
    }
  }

  if (
    hourNum !== null &&
    minuteNum !== null &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*'
  ) {
    return {
      mode: 'daily',
      timeHour: hourNum,
      timeMinute: minuteNum,
      timeSecond: secondNum,
    }
  }

  if (
    dayOfWeekNum !== null &&
    dayOfMonth === '*' &&
    month === '*' &&
    hourNum !== null &&
    minuteNum !== null
  ) {
    const normalizedDay = dayOfWeekNum === 7 ? 0 : dayOfWeekNum
    if (normalizedDay < 0 || normalizedDay > 6) {
      return { mode: 'custom', customExpression: expression }
    }

    return {
      mode: 'weekly',
      dayOfWeek: normalizedDay,
      timeHour: hourNum,
      timeMinute: minuteNum,
      timeSecond: secondNum,
    }
  }

  if (
    dayOfMonthNum !== null &&
    month === '*' &&
    dayOfWeek === '*' &&
    hourNum !== null &&
    minuteNum !== null
  ) {
    if (dayOfMonthNum < 1 || dayOfMonthNum > 31) {
      return { mode: 'custom', customExpression: expression }
    }

    return {
      mode: 'monthly',
      dayOfMonth: dayOfMonthNum,
      timeHour: hourNum,
      timeMinute: minuteNum,
      timeSecond: secondNum,
    }
  }

  return { mode: 'custom', customExpression: expression }
}

function isSimpleField(value: string): boolean {
  return value === '*' || /^\d+$/.test(value) || /^\*\/\d+$/.test(value)
}

function parseNumber(value: string): number | null {
  return /^\d+$/.test(value) ? parseInt(value, 10) : null
}

function parseStep(value: string): number | null {
  if (!/^\*\/\d+$/.test(value)) return null
  const step = parseInt(value.slice(2), 10)
  return Number.isFinite(step) && step > 0 ? step : null
}
</script>

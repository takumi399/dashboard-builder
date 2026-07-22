import assert from 'node:assert/strict';
import test from 'node:test';

import { chartPropertyPatch } from '../src/utils/chartProperties.ts';

test('chartPropertyPatch ignores cleared numeric controls', () => {
  assert.equal(chartPropertyPatch('width', null), null);
  assert.equal(chartPropertyPatch('height', null), null);
});

test('chartPropertyPatch preserves valid editable values', () => {
  assert.deepEqual(chartPropertyPatch('title', 'Revenue'), { title: 'Revenue' });
  assert.deepEqual(chartPropertyPatch('width', 640), { width: 640 });
  assert.deepEqual(chartPropertyPatch('data_source_id', null), { data_source_id: null });
});

test('chartPropertyPatch normalizes a cleared data source to null', () => {
  assert.deepEqual(chartPropertyPatch('data_source_id', undefined), { data_source_id: null });
});

function invalidFieldValuePairsAreRejectedByTypeScript() {
  // @ts-expect-error title only accepts strings
  chartPropertyPatch('title', 640);
  // @ts-expect-error width only accepts numbers or the control's null clear value
  chartPropertyPatch('width', '640');
  // @ts-expect-error this handler cannot edit chart_type
  chartPropertyPatch('chart_type', 'bar');
}

void invalidFieldValuePairsAreRejectedByTypeScript;

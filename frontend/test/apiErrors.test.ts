import assert from 'node:assert/strict';
import test from 'node:test';

import { apiErrorMessage, isFormValidationError } from '../src/utils/apiErrors.ts';

const axiosError = (data: unknown): unknown => ({
  isAxiosError: true,
  response: { data },
});

test('apiErrorMessage falls back for FastAPI array details', () => {
  const detail = [{ type: 'missing', loc: ['body', 'name'], msg: 'Field required' }];

  assert.equal(apiErrorMessage(axiosError({ detail }), 'Request failed'), 'Request failed');
});

test('apiErrorMessage falls back for object details', () => {
  assert.equal(
    apiErrorMessage(axiosError({ detail: { message: 'not a string' } }), 'Request failed'),
    'Request failed',
  );
});

test('apiErrorMessage returns string details', () => {
  assert.equal(apiErrorMessage(axiosError({ detail: 'Specific failure' }), 'Request failed'), 'Specific failure');
});

test('isFormValidationError requires errorFields to be an array', () => {
  assert.equal(isFormValidationError({ errorFields: { name: ['Required'] } }), false);
  assert.equal(isFormValidationError({ errorFields: [] }), true);
});

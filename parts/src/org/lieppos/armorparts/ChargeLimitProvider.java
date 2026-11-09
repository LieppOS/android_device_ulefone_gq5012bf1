/*
 * Dynamic summary for the injected Settings > Battery > Charge limit entry
 * ("com.android.settings.summary_uri"). Settings calls getDynamicSummary and
 * observes ChargeLimit.SUMMARY_URI for changes. Read-only; serves nothing else.
 */
package org.lieppos.armorparts;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;

public class ChargeLimitProvider extends ContentProvider {
    private static final String METHOD_GET_DYNAMIC_SUMMARY = "getDynamicSummary";
    private static final String META_DATA_PREFERENCE_SUMMARY = "com.android.settings.summary";

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public Bundle call(String method, String arg, Bundle extras) {
        if (!METHOD_GET_DYNAMIC_SUMMARY.equals(method)) return null;
        Bundle result = new Bundle();
        result.putString(META_DATA_PREFERENCE_SUMMARY, ChargeLimit.summary(getContext()));
        return result;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs,
            String sortOrder) {
        return null;
    }

    @Override
    public String getType(Uri uri) {
        return null;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        throw new UnsupportedOperationException();
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException();
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException();
    }
}

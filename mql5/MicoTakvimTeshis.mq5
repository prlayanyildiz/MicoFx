//+------------------------------------------------------------------+
//| MicoTakvimTeshis.mq5                                             |
//| The export came back with a header and no rows, which means      |
//| CalendarValueHistory returned nothing. That has several possible |
//| causes and they need different fixes, so ask the calendar what   |
//| it actually has before guessing.                                 |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

void OnStart()
{
   PrintFormat("--- MicoTakvim teshis | terminal %s build %d",
               TerminalInfoString(TERMINAL_NAME), TerminalInfoInteger(TERMINAL_BUILD));
   PrintFormat("bagli=%s  sunucu=%s",
               (string)TerminalInfoInteger(TERMINAL_CONNECTED),
               AccountInfoString(ACCOUNT_SERVER));

   // Does the calendar database exist at all? Countries come from the same
   // store as values; empty here means nothing was ever downloaded.
   MqlCalendarCountry ulkeler[];
   ResetLastError();
   int nu = CalendarCountryById(0, ulkeler[0]) ? 1 : 0;
   nu = 0;
   MqlCalendarCountry liste[];
   ResetLastError();
   int toplamUlke = CalendarCountries(liste);
   PrintFormat("CalendarCountries -> %d (hata %d)", toplamUlke, GetLastError());

   // Events for one big currency, no time filter.
   MqlCalendarEvent olaylar[];
   ResetLastError();
   int nOlay = CalendarEventByCurrency("USD", olaylar);
   PrintFormat("CalendarEventByCurrency(USD) -> %d (hata %d)", nOlay, GetLastError());

   // Values across a narrow recent window, then a wide one.
   datetime simdi = TimeCurrent();
   MqlCalendarValue dar[];
   ResetLastError();
   int nDar = CalendarValueHistory(dar, simdi - 14 * 24 * 60 * 60, simdi + 7 * 24 * 60 * 60, NULL, NULL);
   PrintFormat("CalendarValueHistory(son 14g) -> %d (hata %d)", nDar, GetLastError());

   MqlCalendarValue genis[];
   ResetLastError();
   int nGenis = CalendarValueHistory(genis, simdi - 400 * 24 * 60 * 60, simdi + 30 * 24 * 60 * 60, NULL, NULL);
   PrintFormat("CalendarValueHistory(400g) -> %d (hata %d)", nGenis, GetLastError());

   PrintFormat("TimeCurrent=%s  TimeLocal=%s",
               TimeToString(simdi, TIME_DATE | TIME_MINUTES),
               TimeToString(TimeLocal(), TIME_DATE | TIME_MINUTES));
   Print("--- teshis bitti. Hata 4014 = takvim kapali/desteklenmiyor.");
}
//+------------------------------------------------------------------+

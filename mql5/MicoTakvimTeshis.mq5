//+------------------------------------------------------------------+
//| MicoTakvimTeshis.mq5                                             |
//| The export keeps returning 5401 (calendar timeout). That has     |
//| several causes needing different fixes, so ask the calendar what |
//| it holds before guessing. Writes no file; prints and stops.      |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

void OnStart()
{
   PrintFormat("--- MicoTakvim teshis | build %d | bagli=%d | sunucu=%s",
               (int)TerminalInfoInteger(TERMINAL_BUILD),
               (int)TerminalInfoInteger(TERMINAL_CONNECTED),
               AccountInfoString(ACCOUNT_SERVER));

   // Countries come from the same local store as values. Zero here means the
   // calendar database is empty, which is a download problem, not a query one.
   MqlCalendarCountry ulkeler[];
   ResetLastError();
   int nUlke = CalendarCountries(ulkeler);
   PrintFormat("CalendarCountries -> %d (hata %d)", nUlke, GetLastError());

   MqlCalendarEvent olaylar[];
   ResetLastError();
   int nOlay = CalendarEventByCurrency("USD", olaylar);
   PrintFormat("CalendarEventByCurrency(USD) -> %d (hata %d)", nOlay, GetLastError());

   datetime simdi = TimeCurrent();
   int pencereler[] = {1, 7, 30, 180};
   for(int i = 0; i < ArraySize(pencereler); i++)
   {
      MqlCalendarValue v[];
      ResetLastError();
      int n = CalendarValueHistory(v, simdi - (datetime)pencereler[i] * 24 * 60 * 60, simdi, NULL, NULL);
      PrintFormat("CalendarValueHistory(son %d gun) -> %d (hata %d)",
                  pencereler[i], n, GetLastError());
   }

   // Same query narrowed to one country: a per-country request is smaller and
   // sometimes answers when the unfiltered one times out.
   MqlCalendarValue us[];
   ResetLastError();
   int nUs = CalendarValueHistoryByEvent(840000013, us, simdi - 180 * 24 * 60 * 60, simdi);
   PrintFormat("CalendarValueHistoryByEvent(ABD ornek) -> %d (hata %d)", nUs, GetLastError());

   PrintFormat("TimeCurrent=%s TimeLocal=%s",
               TimeToString(simdi, TIME_DATE | TIME_MINUTES),
               TimeToString(TimeLocal(), TIME_DATE | TIME_MINUTES));
   Print("--- bitti. 5401=zaman asimi, 5402=veri yok, 4014=desteklenmiyor.");
}
//+------------------------------------------------------------------+

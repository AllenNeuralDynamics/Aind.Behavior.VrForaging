using System;
using System.Collections.Generic;

namespace Extensions.Tests
{
    /// <summary>
    /// Deterministic fake random generator fixture used by tests.
    /// </summary>
    /// <remarks>
    /// <para>
    /// This helper allows tests to predefine values returned by <see cref="NextDouble"/> and
    /// <see cref="Next(int)"/>, making sampling behavior reproducible and non-flaky.
    /// </para>
    /// <para>
    /// If queued values are exhausted, configured default values are used.
    /// </para>
    /// </remarks>
    internal sealed class QueueRandom : Random
    {
        private readonly Queue<double> _doubles;
        private readonly Queue<int> _ints;
        private readonly double _defaultDouble;
        private readonly int _defaultInt;

        /// <summary>
        /// Creates a deterministic random source backed by optional queues for doubles and ints.
        /// </summary>
        /// <param name="doubles">Sequence returned by <see cref="NextDouble"/> before falling back to <paramref name="defaultDouble"/>.</param>
        /// <param name="ints">Sequence returned by <see cref="Next(int)"/> before falling back to <paramref name="defaultInt"/>.</param>
        /// <param name="defaultDouble">Fallback value used when the double queue is empty.</param>
        /// <param name="defaultInt">Fallback value used when the int queue is empty.</param>
        public QueueRandom(IEnumerable<double> doubles = null, IEnumerable<int> ints = null, double defaultDouble = 0.0, int defaultInt = 0)
        {
            _doubles = new Queue<double>(doubles ?? Array.Empty<double>());
            _ints = new Queue<int>(ints ?? Array.Empty<int>());
            _defaultDouble = defaultDouble;
            _defaultInt = defaultInt;
        }

        /// <summary>
        /// Returns the next queued double, or the configured default when the queue is empty.
        /// </summary>
        public override double NextDouble()
        {
            return _doubles.Count > 0 ? _doubles.Dequeue() : _defaultDouble;
        }

        /// <summary>
        /// Returns the next queued integer normalized to <c>[0, maxValue)</c>, or a normalized default value when empty.
        /// </summary>
        /// <param name="maxValue">Exclusive upper bound.</param>
        /// <returns>A deterministic value in range for a given <paramref name="maxValue"/>.</returns>
        public override int Next(int maxValue)
        {
            if (maxValue <= 0)
            {
                return 0;
            }

            var value = _ints.Count > 0 ? _ints.Dequeue() : _defaultInt;
            if (value < 0)
            {
                value = -value;
            }
            return value % maxValue;
        }
    }
}
